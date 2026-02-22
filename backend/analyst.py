import os
import sys
import warnings
import ccxt
import numpy as np
import pandas as pd
import pandas_ta as ta
import time
import subprocess
from datetime import datetime, timedelta

# --- [0. 시스템 환경 설정] ---
warnings.filterwarnings("ignore")
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

# --- [1. 시스템 설정] ---
SYMBOL = 'BTC/USDT'
TIMEFRAMES = ['1d', '4h', '1h']
LIMIT = 1000            # 지표 계산 정밀도를 위해 충분한 데이터 확보
BALANCE = 1000.0        # 가용 자산 (USDT)
RISK_PER_TRADE = 0.02   # 1회 매매 시 최대 손실 2%

# --- [2. 실시간 데이터 수집 엔진] ---
class MarketDataFetcher:
    def __init__(self, symbol):
        self.symbol = symbol
        self.exchange = ccxt.binance({'options': {'defaultType': 'future'}})

    def fetch_ohlcv(self, tf):
        """실시간 OHLCV 및 Taker Volume 수집"""
        try:
            params = {'symbol': self.symbol.replace('/', ''), 'interval': tf, 'limit': LIMIT}
            ohlcv = self.exchange.fapiPublicGetKlines(params)
            cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'q_vol', 'trades', 'taker_buy_vol', 'taker_buy_quote_vol', 'ignore']
            df = pd.DataFrame(ohlcv, columns=cols)
            for c in ['open', 'high', 'low', 'close', 'volume', 'taker_buy_vol']:
                df[c] = pd.to_numeric(df[c], errors='coerce')
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            print(f"[Error] OHLCV 수집 실패 ({tf}): {e}")
            return pd.DataFrame()

    def fetch_context(self):
        """실시간 OI 및 펀딩비 수집"""
        try:
            funding = self.exchange.fetch_funding_rate(self.symbol)
            fr = funding['fundingRate'] * 100 if funding else 0.0
            oi_res = self.exchange.fapiPublicGetOpenInterest({'symbol': self.symbol.replace('/', '')})
            oi = float(oi_res['openInterest']) if oi_res else 0.0
            return round(fr, 4), oi
        except:
            return 0.0, 0.0

# --- [3. 기술적 분석 엔진 (backtest.py와 로직 100% 동일)] ---
class TechnicalAnalyzer:
    @staticmethod
    def apply_indicators(df):
        if len(df) < 50: return df
        df = df.copy()
        df['ema_20'] = ta.ema(df['close'], length=20)
        df['ema_50'] = ta.ema(df['close'], length=50)
        df['rsi'] = ta.rsi(df['close'], length=14)
        adx_res = ta.adx(df['high'], df['low'], df['close'], length=14)
        df['adx'] = adx_res['ADX_14'] if adx_res is not None else 0
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['date'] = df.index.date
        df['pv'] = df['typical_price'] * df['volume']
        groups = df.groupby('date')
        df['vwap'] = groups['pv'].cumsum() / groups['volume'].cumsum()
        
        df['taker_sell_vol'] = df['volume'] - df['taker_buy_vol']
        df['delta'] = df['taker_buy_vol'] - df['taker_sell_vol']
        df['cvd'] = groups['delta'].cumsum()
        return df

    @staticmethod
    def check_divergence(df, window=10):
        if len(df) < window * 2: return "➖ 없음", "➖ 없음"
        recent, prev = df.iloc[-window:], df.iloc[-(window*2):-window]
        cvd_div = "➖ 동기화됨"
        if recent['high'].max() > prev['high'].max() and recent['cvd'].max() < prev['cvd'].max():
            cvd_div = "📉 하락 다이버전스 (수급 고갈)"
        elif recent['low'].min() < prev['low'].min() and recent['cvd'].min() > prev['cvd'].min():
            cvd_div = "📈 상승 다이버전스 (매집 징후)"
        rsi_div = "➖ 없음"
        if recent['low'].min() > prev['low'].min() and recent['rsi'].min() < prev['rsi'].min():
            rsi_div = "🟢 강세 히든 (상승 눌림목)"
        elif recent['high'].max() < prev['high'].max() and recent['rsi'].max() > prev['rsi'].max():
            rsi_div = "🔴 약세 히든 (하락 반등)"
        return cvd_div, rsi_div

    @staticmethod
    def get_avp(df):
        sliced_df = df.tail(300)
        price, volume = sliced_df['close'].values, sliced_df['volume'].values
        hist, bin_edges = np.histogram(price, bins=50, weights=volume)
        max_idx = np.argmax(hist)
        poc = (bin_edges[max_idx] + bin_edges[max_idx + 1]) / 2
        target_vol = np.sum(hist) * 0.7
        current_vol, l_idx, u_idx = hist[max_idx], max_idx, max_idx
        while current_vol < target_vol and (l_idx > 0 or u_idx < len(hist) - 1):
            v_l = hist[l_idx - 1] if l_idx > 0 else -1
            v_u = hist[u_idx + 1] if u_idx < len(hist) - 1 else -1
            if v_l > v_u: l_idx -= 1; current_vol += hist[l_idx]
            else: u_idx += 1; current_vol += hist[u_idx]
        return float(poc), float(bin_edges[u_idx+1]), float(bin_edges[l_idx]), len(sliced_df)

    @staticmethod
    def get_smc(df, lookback=200):
        df_recent = df.iloc[-lookback:].copy()
        if len(df_recent) < 20: return [], []
        df_recent['vol_sma'] = df_recent['volume'].rolling(20).mean()
        df_recent['atr'] = ta.atr(df_recent['high'], df_recent['low'], df_recent['close'], length=14)
        unmit_fvgs, unmit_obs = [], []
        for i in range(2, len(df_recent) - 1):
            c1_h, c1_l = df_recent['high'].iloc[i-2], df_recent['low'].iloc[i-2]
            c3_h, c3_l = df_recent['high'].iloc[i], df_recent['low'].iloc[i]
            gap = abs(c1_h - c3_l) if c1_h < c3_l else abs(c1_l - c3_h)
            atr_i = df_recent['atr'].iloc[i]
            if c1_h < c3_l and gap > atr_i * 0.5:
                unmit_fvgs.append({'type': '강세 FVG', 'top': c3_l, 'bottom': c1_h, 'idx': i})
            elif c1_l > c3_h and gap > atr_i * 0.5:
                unmit_fvgs.append({'type': '약세 FVG', 'top': c1_l, 'bottom': c3_h, 'idx': i})
            body = abs(df_recent['close'].iloc[i] - df_recent['open'].iloc[i])
            if body > (atr_i * 1.8) and df_recent['volume'].iloc[i] > (df_recent['vol_sma'].iloc[i] * 1.5):
                if df_recent['close'].iloc[i] > df_recent['open'].iloc[i]: 
                    for j in range(i-1, max(0, i-5), -1):
                        if df_recent['close'].iloc[j] < df_recent['open'].iloc[j]:
                            unmit_obs.append({'type': '강세 OB', 'top': df_recent['high'].iloc[j], 'bottom': df_recent['low'].iloc[j], 'idx': j})
                            break
                else: 
                    for j in range(i-1, max(0, i-5), -1):
                        if df_recent['close'].iloc[j] > df_recent['open'].iloc[j]:
                            unmit_obs.append({'type': '약세 OB', 'top': df_recent['high'].iloc[j], 'bottom': df_recent['low'].iloc[j], 'idx': j})
                            break
        v_fvgs, v_obs = [], []
        for f in unmit_fvgs:
            sub = df_recent.iloc[f['idx']+1:]
            if f['type'] == '강세 FVG' and sub['low'].min() < f['bottom']: continue
            if f['type'] == '약세 FVG' and sub['high'].max() > f['top']: continue
            v_fvgs.append(f)
        for o in unmit_obs:
            sub = df_recent.iloc[o['idx']+1:]
            if o['type'] == '강세 OB' and sub['low'].min() < o['bottom']: continue
            if o['type'] == '약세 OB' and sub['high'].max() > o['top']: continue
            v_obs.append(o)
        return v_fvgs[-2:], v_obs[-2:]

# --- [4. 정밀 프롬프트 생성기] ---
def generate_report():
    fetcher = MarketDataFetcher(SYMBOL)
    print(f"[{SYMBOL}] 실시간 데이터 수집 및 분석 중...")
    fr, oi = fetcher.fetch_context()
    
    tf_results, current_price = {}, 0
    for tf in TIMEFRAMES:
        df = fetcher.fetch_ohlcv(tf)
        if df.empty: continue
        df = TechnicalAnalyzer.apply_indicators(df)
        latest = df.iloc[-1]
        current_price = latest['close']
        poc, vah, val, look = TechnicalAnalyzer.get_avp(df)
        fvgs, obs = TechnicalAnalyzer.get_smc(df)
        cvd_div, rsi_div = TechnicalAnalyzer.check_divergence(df)
        
        f_strs = [f"{f['type']}: {f['bottom']:.0f}~{f['top']:.0f}" for f in fvgs]
        o_strs = [f"{o['type']}: {o['bottom']:.0f}~{o['top']:.0f}" for o in obs]
        
        tf_results[tf] = {
            'close': current_price, 'vwap': latest['vwap'], 'poc': poc, 'vah': vah, 'val': val, 'lookback': look,
            'cvd_div': cvd_div, 'hidden_rsi_div': rsi_div,
            'fvgs': ", ".join(f_strs) if f_strs else "없음",
            'obs': ", ".join(o_strs) if o_strs else "없음",
            'atr': latest['atr'], 'rsi': latest['rsi'], 'adx': latest['adx'],
            'trend': "정배열(상승)" if latest['ema_20'] > latest['ema_50'] else "역배열(하락)"
        }

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # [수행 지시사항 - 변경 금지]
    prompt = f"""당신은 퀀트 헤지펀드의 수석 AI 알고리즘입니다. (시점: {now_str})
현재 비트코인(BTC) 시장 상황을 정밀 분석하여 보고서를 상신합니다. 

🚨 **[시장 상태]**: 정기 분석 보고 (실시간 데이터 연동)
👉 현재가: {current_price:.2f}

### 📊 거시적 유동성 및 심리
- 미결제약정(OI): {oi:,.0f} | 펀딩비: {fr:.4f}%

### 📈 타임프레임별 미세구조 (SMC & 수급)
"""
    for tf, d in tf_results.items():
        prompt += f"""
**[{tf} 차트]**
- **추세/동력:** EMA {d['trend']} (ADX: {d['adx']:.1f}) / RSI: {d['rsi']:.1f}
- **기관 수급(정밀):** CVD {d['cvd_div']} / RSI 히든: {d['hidden_rsi_div']}
- **매물대 (AVP {d['lookback']}캔들):** VAH {d['vah']:.0f} / POC {d['poc']:.0f} / VAL {d['val']:.0f}
- **SMC (공진화 구역):** 
  - 미완화 OB: {d['obs']}
  - 미완화 FVG: {d['fvgs']}
- **기관 평단가 (Daily VWAP):** {d['vwap']:.2f}
"""
    prompt += f"""
---
### 🤖 [수행 지시사항: 퀀트 전략 수립 프로토콜]

**Phase 1. 다중 요소 정량 평가 (Quant Factor Assessment)**
- 아래 4가지 요소를 분석하여 '진입 신뢰도(0-100%)'를 산출하십시오. 분석 시 Real Taker Volume 기반의 CVD 신뢰도를 최우선 하십시오.
  1. **추세 신뢰도 (Trend):** EMA 정/역배열 상태 및 ADX 강도를 분석하여 추세의 지속성 평가.
  2. **수급 동기화 (Liquidity/CVD):** 현재가와 CVD 다이버전스 상태, 그리고 기관 평단가(VWAP)와의 이격을 분석.
  3. **구조적 부합성 (Structure):** 현재가가 주요 SMC(OB, FVG) 및 매물대(POC, VA)의 기술적 합일점(Confluence)에 있는지 평가.
  4. **변동성 상태 (Volatility):** ATR 기준으로 현재 위치가 비정상적 변동성 범위에 있는지 확인.

**Phase 2. 확률적 가설 수립 및 기대값(EV) 최적화**
- 선택한 방향이 수학적으로 기대값(Expected Value)이 플러스(+)인 이유를 논리적으로 증명하십시오.
- 타겟 방향의 매물대 공백(Liquidity Void)과 반대 방향의 저항 강도를 비교하여 확률적 우위를 도출하십시오.

**Phase 3. 수학적 매매 매개변수 산출 (Parameter Optimization)**
1. **매매 스타일:** [스캘핑 / 데이트레이딩 / 스윙] 중 데이터에 가장 적합한 전략 확정.
2. **포지션:** [LONG / SHORT / Wait]
3. **진입가(Entry):** 주요 구조물이 중첩되는 '기술적 합일점'을 정밀하게 제시하십시오. **특히 역추세 진입 시 추세 강도와 수급 상태를 분석하여 매물대 이탈(Sweep) 폭을 상황에 맞게 유연하게 조정하고, 확증적 변곡 지점을 정밀한 진입가로 산출하십시오.**
4. **손절가(SL):** 단순히 ATR 수치만 가감하지 마십시오. **주요 구조물(OB/FVG/매물대)이 완전히 파괴되는 지점으로부터 1시간봉 ATR({tf_results['1h']['atr']:.2f})의 0.5배만큼 추가 여유(Buffer)**를 두어 휩소(Sweep)를 방어할 수 있는 최종 경계선에 설정하십시오.
5. **목표가(TP):** 최소 손익비 1:1.5를 보장하되, 목표가를 주요 매물대(POC, VWAP)나 저항선 끝단에 정밀하게 맞추지 마십시오. 가격이 도달하기 직전에 반대 방향 OB에 맞고 튕길 수 있으므로, **주요 저항선 0.5~1% 직전**에 설정하여 확실한 수익 실현을 우선하십시오.
6. **자금 관리 (2% 정밀 계산):**
   - 최대 허용 손실액: ${BALANCE * RISK_PER_TRADE:.2f} (잔고의 2%)
   - **권장 투입 수량(Qty):** {(BALANCE * RISK_PER_TRADE):.2f} / |진입가 - 손절가| 공식으로 계산하여 소수점 3자리까지 제시하십시오.

**Phase 4. 최종 전략 요약**
- 위 단계를 거쳐 도출된 최종 전략의 핵심 근거를 퀀트 보고서 형식으로 2줄 요약하십시오.
"""
    return prompt

if __name__ == "__main__":
    report = generate_report()
    if report:
        print("\n" + "="*85 + "\n" + report)
        try:
            process = subprocess.Popen(['clip.exe'], stdin=subprocess.PIPE, shell=True)
            process.communicate(input=report.encode('utf-16'))
            print("="*85 + "\n📋 클립보드에 복사되었습니다. AI에게 전달하세요!\n" + "="*85)
        except: pass
