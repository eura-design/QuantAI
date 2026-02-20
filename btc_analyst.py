import ccxt
import time
import sys
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime

# 한글 출력 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# 1. 설정 (바이낸스 선물 시장)
symbol = 'BTC/USDT'
timeframes = ['1h', '4h', '1d']
limit = 500  # 충분한 데이터 확보 (OB 추적용)

def fetch_data(tf):
    """바이낸스에서 데이터 가져오기 (Taker Buy Volume 포함)"""
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    
    params = {
        'symbol': symbol.replace('/', ''),
        'interval': tf,
        'limit': limit
    }
    try:
        ohlcv = exchange.fapiPublicGetKlines(params)
        cols = [
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'num_trades', 'taker_buy_vol', 'taker_buy_quote_vol', 'ignore'
        ]
        df = pd.DataFrame(ohlcv, columns=cols)
        
        cols_numeric = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'taker_buy_vol']
        df[cols_numeric] = df[cols_numeric].apply(pd.to_numeric)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        # CVD 계산 (Delta = Taker Buy - Taker Sell)
        df['taker_sell_vol'] = df['volume'] - df['taker_buy_vol']
        df['delta'] = df['taker_buy_vol'] - df['taker_sell_vol']
        df['cvd'] = df['delta'].cumsum()
        
        return df
    except Exception as e:
        print(f"[Error] fetch_data({tf}): {e}")
        return pd.DataFrame()

def detect_rsi_divergence_realtime(df):
    """
    [리페인팅 방지] 3-Candle 패턴을 이용한 실시간 RSI 다이버전스 감지
    """
    if len(df) < 50: return "데이터 부족"
    
    rsi = df['RSI'].values
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    
    peaks = []
    troughs = []
    
    for i in range(len(df) - 50, len(df)):
        if i < 2: continue
        if rsi[i-2] <= rsi[i-1] and rsi[i-1] > rsi[i]:
            peaks.append((i-1, rsi[i-1], high[i-1])) 
        if rsi[i-2] >= rsi[i-1] and rsi[i-1] < rsi[i]:
            troughs.append((i-1, rsi[i-1], low[i-1])) 
            
    result = "없음"
    
    if len(peaks) >= 2:
        last_p = peaks[-1]
        prev_p = peaks[-2]
        if len(df) - 1 - last_p[0] <= 5:
            if last_p[2] > prev_p[2] and last_p[1] < prev_p[1]:
                result = "하락 다이버전스 (Bearish Div)"

    if len(troughs) >= 2:
        last_t = troughs[-1]
        prev_t = troughs[-2]
        if len(df) - 1 - last_t[0] <= 5:
            if last_t[2] < prev_t[2] and last_t[1] > prev_t[1]:
                result = "상승 다이버전스 (Bullish Div)"
                
    return result

def calculate_volume_profile(df, bins=50):
    """[최적화] numpy.histogram을 이용한 Volume Profile 계산"""
    if len(df) < 50: return {'poc': 0, 'vah': 0, 'val': 0}
    
    lookback = min(len(df), 300)
    data = df.tail(lookback)
    
    price = data['close'].values
    volume = data['volume'].values
    
    hist, bin_edges = np.histogram(price, bins=bins, weights=volume)
    
    max_idx = np.argmax(hist)
    poc = (bin_edges[max_idx] + bin_edges[max_idx+1]) / 2
    
    total_vol = np.sum(hist)
    target_vol = total_vol * 0.7
    
    current_vol = hist[max_idx]
    lower_idx = max_idx
    upper_idx = max_idx
    
    while current_vol < target_vol:
        can_go_lower = lower_idx > 0
        can_go_upper = upper_idx < bins - 1
        
        vol_lower = hist[lower_idx-1] if can_go_lower else 0
        vol_upper = hist[upper_idx+1] if can_go_upper else 0
        
        if not can_go_lower and not can_go_upper:
            break
            
        if vol_upper > vol_lower:
            upper_idx += 1
            current_vol += hist[upper_idx]
        else:
            lower_idx -= 1
            current_vol += hist[lower_idx]
            
    vah = bin_edges[upper_idx+1]
    val = bin_edges[lower_idx]
    
    return {'poc': poc, 'vah': vah, 'val': val}

def calculate_vwap(df):
    """VWAP (Volume Weighted Average Price) 계산"""
    tp = (df['high'] + df['low'] + df['close']) / 3
    vwap = (tp * df['volume']).cumsum() / df['volume'].cumsum()
    return vwap

def detect_liquidity_sweep(df, lookback=30):
    """Liquidity Sweep (유동성 탈취) 탐지"""
    if len(df) < lookback + 5: return "없음"
    
    hist = df.iloc[-(lookback+1):-1]
    prev_high = hist['high'].max()
    prev_low = hist['low'].min()
    
    curr = df.iloc[-1]
    
    if curr['high'] > prev_high and curr['close'] < prev_high:
        return f"하락 유동성 탈취 (Bearish Sweep targets {prev_high:.1f})"
    
    if curr['low'] < prev_low and curr['close'] > prev_low:
        return f"상승 유동성 탈취 (Bullish Sweep targets {prev_low:.1f})"
    
    return "없음"

def detect_cvd_divergence(df, lookback=30):
    """CVD 다이버전스 탐지"""
    if len(df) < lookback: return "없음"
    
    close = df['close'].values
    cvd = df['cvd'].values
    
    subset_close = close[-lookback:]
    subset_cvd = cvd[-lookback:]
    
    price_min_idx = np.argmin(subset_close)
    price_max_idx = np.argmax(subset_close)
    cvd_min_idx = np.argmin(subset_cvd)
    cvd_max_idx = np.argmax(subset_cvd)
    
    if price_min_idx > cvd_min_idx and subset_close[price_min_idx] < subset_close[cvd_min_idx] and subset_cvd[price_min_idx] > subset_cvd[cvd_min_idx]:
        return "강력 상승 다이버전스 (CVD Bullish Div - 매도 흡수)"
        
    if price_max_idx > cvd_max_idx and subset_close[price_max_idx] > subset_close[cvd_max_idx] and subset_cvd[price_max_idx] < subset_cvd[cvd_max_idx]:
        return "강력 하락 다이버전스 (CVD Bearish Div - 매수 흡수)"
        
    return "없음"

def detect_smc_structure(df):
    """[SMC 핵심] Order Block(OB) 및 FVG 탐지"""
    if len(df) < 50: return {'obs': [], 'fvgs': []}
    
    obs = []
    fvgs = []
    
    open_p = df['open'].values
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    volume = df['volume'].values
    vol_sma = df['volume'].rolling(20).mean().fillna(0).values
    
    for i in range(2, len(df)):
        # Mitigation Check
        curr_low = low[i]
        curr_high = high[i]
        
        for ob in obs:
            if ob['mitigated']: continue
            if ob['type'] == 'BuOB' and curr_low <= ob['top']: ob['mitigated'] = True
            elif ob['type'] == 'BeOB' and curr_high >= ob['bottom']: ob['mitigated'] = True
                
        for fvg in fvgs:
            if fvg['mitigated']: continue
            if fvg['type'] == 'BuFVG' and curr_low <= fvg['top']: fvg['mitigated'] = True
            elif fvg['type'] == 'BeFVG' and curr_high >= fvg['bottom']: fvg['mitigated'] = True

        # FVG 생성
        if low[i] > high[i-2]:
            gap = low[i] - high[i-2]
            if gap > (high[i] - low[i]) * 0.1: 
                fvgs.append({'type': 'BuFVG', 'top': float(low[i]), 'bottom': float(high[i-2]), 'mitigated': False, 'index': i})
        
        if high[i] < low[i-2]:
            gap = low[i-2] - high[i]
            if gap > (high[i] - low[i]) * 0.1:
                fvgs.append({'type': 'BeFVG', 'top': float(low[i-2]), 'bottom': float(high[i]), 'mitigated': False, 'index': i})
        
        # Order Block 생성
        lookback = 20
        local_high = np.max(high[i-lookback:i]) if i > lookback else high[i-1]
        local_low = np.min(low[i-lookback:i]) if i > lookback else low[i-1]
        
        # Bullish OB
        if close[i] > open_p[i] and close[i-1] < open_p[i-1]: 
             if close[i] > local_high and volume[i] > vol_sma[i] * 1.5:
                obs.append({'type': 'BuOB', 'top': float(open_p[i-1]), 'bottom': float(low[i-1]), 'mitigated': False, 'index': i-1})
                    
        # Bearish OB
        if close[i] < open_p[i] and close[i-1] > open_p[i-1]: 
            if close[i] < local_low and volume[i] > vol_sma[i] * 1.5:
                obs.append({'type': 'BeOB', 'top': float(high[i-1]), 'bottom': float(open_p[i-1]), 'mitigated': False, 'index': i-1})
    
    return {
        'obs': [ob for ob in obs if not ob['mitigated']][-3:], 
        'fvgs': [fvg for fvg in fvgs if not fvg['mitigated']][-3:]
    }

def analyze_data(df):
    """SMC 중심 통합 분석"""
    try:
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
        df['ADX'] = adx_df['ADX_14']
        df['VWAP'] = calculate_vwap(df)
        df['EMA200'] = ta.ema(df['close'], length=200)
    except:
        df['RSI'] = 50
        df['ATR'] = 0
        df['ADX'] = 0
        df['VWAP'] = df['close']
    
    vp = calculate_volume_profile(df, bins=100)
    smc = detect_smc_structure(df)
    rsi_div = detect_rsi_divergence_realtime(df)
    lq_sweep = detect_liquidity_sweep(df)
    cvd_div = detect_cvd_divergence(df)
    
    cvd_slope = 0
    if len(df) >= 50:
        y = df['cvd'].tail(50).values
        x = np.arange(len(y))
        cvd_slope = np.polyfit(x, y, 1)[0]

    latest = df.iloc[-1].copy()
    
    return {
        'close': float(latest['close']),
        'rsi': float(latest['RSI']),
        'atr': float(latest['ATR']),
        'adx': float(latest['ADX']) if not pd.isna(latest['ADX']) else 0,
        'vwap': float(latest['VWAP']),
        'ema200': float(latest['EMA200']) if not pd.isna(latest['EMA200']) else float(latest['close']),
        'vp': vp,
        'smc': smc,
        'rsi_div': rsi_div,
        'cvd_div': cvd_div,
        'lq_sweep': lq_sweep,
        'cvd_slope': cvd_slope,
        'cvd_val': float(latest['cvd']),
        'current_vol': float(latest['volume'])
    }

def fetch_market_info():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    try:
        funding = exchange.fetch_funding_rate(symbol)
        fr = funding['fundingRate'] * 100 if funding else 0
        oi_res = exchange.fapiPublicGetOpenInterest({'symbol': symbol.replace('/', '')})
        oi = float(oi_res['openInterest']) if oi_res else 0
        return fr, oi
    except:
        return 0, 0

def generate_prompt():
    print(f"\n======== [ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} SMC Institutional Analysis (ADX Filtered) ] ========\n")
    
    fr, oi = fetch_market_info()
    
    prompt = ""
    prompt += f"## 1. Market Sentiment & Volatility\n"
    prompt += f"- Funding Rate: {fr:.4f}% ({'Long Squeeze Risk' if fr > 0.02 else 'Short Squeeze Risk' if fr < -0.02 else 'Neutral'})\n"
    prompt += f"- Open Interest: {oi:,.0f}\n"

    try:
        df_d = fetch_data('1d')
        if not df_d.empty:
            today = df_d.iloc[-1]
            today_vol = today['high'] - today['low']
            today_range_pct = (today_vol / today['open']) * 100
            prompt += f"- **Daily Range (Today)**: {today_vol:.2f} USDT ({today_range_pct:.2f}%)\n"
    except:
        pass
    prompt += "\n"
    
    prompt += f"## 2. Technical Breakdown (SMC Focused)\n"
    
    for tf in timeframes:
        df = fetch_data(tf)
        if df.empty: continue
        try:
            res = analyze_data(df)
            
            obs_list = []
            for o in res['smc']['obs']:
                o_type = "Bullish OB" if o['type'] == 'BuOB' else "Bearish OB"
                obs_list.append(f"{o_type} [{o['top']} ~ {o['bottom']}]")
            obs_str = " / ".join(obs_list) if obs_list else "None"
            
            fvgs_list = []
            for f in res['smc']['fvgs']:
                f_type = "Bullish FVG" if f['type'] == 'BuFVG' else "Bearish FVG"
                fvgs_list.append(f"{f_type} [{f['top']} ~ {f['bottom']}]")
            fvgs_str = " / ".join(fvgs_list) if fvgs_list else "None"
            
            vwap_bias = "Premium (고평가)" if res['close'] > res['vwap'] else "Discount (저평가)"
            
            prompt += f"### [{tf} Timeframe]\n"
            prompt += f"- Price: {res['close']:.2f} (VWAP: {res['vwap']:.2f} -> {vwap_bias})\n"
            prompt += f"- **ATR (Volatility)**: {res['atr']:.2f} ({res['atr']/res['close']*100:.2f}%)\n"
            prompt += f"- Volume Profile: POC {res['vp']['poc']:.2f} (Value Area: {res['vp']['val']:.2f} ~ {res['vp']['vah']:.2f})\n"
            prompt += f"- Trend Strength (ADX): {res['adx']:.2f} ({'Strong Trend' if res['adx'] > 25 else 'Weak/Choppy' if res['adx'] < 15 else 'Neutral'})\n"
            prompt += f"- **Order Blocks (Unmitigated)**: {obs_str}\n"
            prompt += f"- **FVGs (Unmitigated)**: {fvgs_str}\n"
            prompt += f"- Liquidity Sweep: {res['lq_sweep']}\n"
            prompt += f"- RSI Divergence: {res['rsi_div']} (RSI: {res['rsi']:.2f})\n"
            prompt += f"- CVD Flow: {res['cvd_div']} (Slope: {res['cvd_slope']:.2f})\n\n"
        except Exception as e:
            prompt += f"[{tf}] Error: {str(e)}\n"

    prompt += f"## 3. Autonomous Performance Strategy (High-End Logic)\n"
    prompt += f"당신은 백테스트를 통해 검증된 지능형 퀀트 시스템입니다. 제공된 모든 데이터(SMC, VWAP, CVD, ADX, RSI 등)의 상관관계를 스스로 분석하여 가중치를 부여하세요.\n\n"
    
    prompt += f"1. **Entry Strategy (Limit Order Focus)**: 실시간 '현재가'에 무조건 진입하지 마세요. 분석된 **Order Block(OB)이나 FVG의 입구 또는 0.5 레벨(중간값)**까지 가격이 도달할 때까지 기다리는 **지정가 진입(Limit Entry)** 전략을 우선적으로 고려하세요.\n"
    prompt += f"2. **Safe Stop Loss (Sweep Resistance)**: 손절가를 단순히 OB/FVG 끝단에 붙이지 마세요. 세력의 유동성 탈취(Liquidity Sweep)를 견딜 수 있도록 **ATR 변동성의 0.5~1배 버퍼**를 더하거나, **직전 스윙 고점/저점(Swing Point)** 너머에 안전하게 설정하세요.\n"
    prompt += f"3. **Risk Control (Immutable)**: 1회 매매 시 전체 자산의 **최대 2%**만 손실되도록 포지션 규모를 반드시 공식(`투입금액 = (자산 * 0.02) / (손절% / 100)`)에 따라 산출하세요. 손절폭이 넓어지면 투입 수량은 그만큼 줄어들어야 합니다.\n"
    prompt += f"4. **Trade Management**: 진입 후 목표가 도달 전이라도 구조적 변화(MSS)가 생기면 본절 이동이나 익절 대응 시나리오를 자율적으로 제시하세요.\n"

    prompt += f"5. 1D(일봉) ADX가 **30 이상인 강한 추세 구간**에서는 추세 반대 방향(역추세) 매매를 금지합니다. 이 경우 **WAIT(관망)**을 선택하거나, 추세 방향으로만 진입하세요.\n\n"
    prompt += f"6. **Exit Strategy Selection**: 시장 상황(Trend vs Range)에 따라 적절한 출구 전략을 선택하세요. 강한 추세장에서는 **Trailing Stop**(수익 극대화)을, 박스권이나 역추세 매매에서는 **Hit & Run**(빠른 익절)을 권장합니다.\n"
    prompt += f"   - 'FULL_EXIT' (100% Take Profit), 'PARTIAL_EXIT' (Scaling Out), 'TRAILING_STOP' (Dynamic Exit)\n"
    prompt += f"   - If 'PARTIAL_EXIT', specify ratio (e.g. 0.5). If 'TRAILING_STOP', specify gap (e.g. 1.5%).\n\n"
    
    prompt += f"## 4. Final Execution Report\n"
    prompt += f"당신의 자율적 분석을 거친 최종 매매 판단[LONG / SHORT / WAIT]과 함께 **지정가 진입가(Limit Entry), 안전 손절가(Safe SL), 목표가(TP1, TP2), 리스크 기반 투입 비중(%), 출구 전략(Exit Type)**을 포함한 전문적인 트레이딩 플랜을 작성하세요.\n"
    
    print(prompt)

if __name__ == "__main__":
    generate_prompt()