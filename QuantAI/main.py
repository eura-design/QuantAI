import os
import sys
import warnings
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime

# 1. 설정
warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass 

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("[ERROR] GEMINI_API_KEY not found.")
    sys.exit(1)

# 최신 라이브러리 클라이언트 초기화
client = genai.Client(api_key=GEMINI_API_KEY)

SYMBOL = 'BTC/USDT'
TIMEFRAMES = ['1h', '4h', '1d']
LIMIT = 500

# 2. 데이터 수집 (CCXT)
def fetch_data(tf):
    print(f"[INFO] Fetching {tf} data from Binance Futures...")
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    params = {'symbol': SYMBOL.replace('/', ''), 'interval': tf, 'limit': LIMIT}
    
    try:
        ohlcv = exchange.fapiPublicGetKlines(params)
        cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_buy_vol', 'taker_buy_quote_vol', 'ignore']
        df = pd.DataFrame(ohlcv, columns=cols)
        
        cols_numeric = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'taker_buy_vol']
        df[cols_numeric] = df[cols_numeric].apply(pd.to_numeric)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        # CVD 계산
        df['taker_sell_vol'] = df['volume'] - df['taker_buy_vol']
        df['delta'] = df['taker_buy_vol'] - df['taker_sell_vol']
        df['cvd'] = df['delta'].cumsum()
        
        return df
    except Exception as e:
        print(f"[ERROR] Fetch failed: {e}")
        return pd.DataFrame()

# 3. 고급 기술적 분석 함수들 (완전체 복구)

def calculate_vwap(df):
    """VWAP Calculation"""
    tp = (df['high'] + df['low'] + df['close']) / 3
    vwap = (tp * df['volume']).cumsum() / df['volume'].cumsum()
    return vwap

def calculate_volume_profile(df):
    """Volume Profile VAH/VAL Calculation"""
    if len(df) < 50: return {'poc': 0, 'vah': 0, 'val': 0}
    price = df['close'].values
    volume = df['volume'].values
    hist, bin_edges = np.histogram(price, bins=100, weights=volume)
    max_idx = np.argmax(hist)
    poc = (bin_edges[max_idx] + bin_edges[max_idx+1]) / 2
    
    total_vol = np.sum(hist)
    target_vol = total_vol * 0.7
    current_vol = hist[max_idx]
    lower_idx = max_idx
    upper_idx = max_idx
    
    while current_vol < target_vol:
        can_go_lower = lower_idx > 0
        can_go_upper = upper_idx < 99
        vol_lower = hist[lower_idx-1] if can_go_lower else 0
        vol_upper = hist[upper_idx+1] if can_go_upper else 0
        
        if not can_go_lower and not can_go_upper: break
        
        if vol_upper > vol_lower:
            upper_idx += 1
            current_vol += hist[upper_idx]
        else:
            lower_idx -= 1
            current_vol += hist[lower_idx]
            
    vah = bin_edges[upper_idx+1]
    val = bin_edges[lower_idx]
    return {'poc': poc, 'vah': vah, 'val': val}

def detect_rsi_divergence(df):
    """[Original] 3-Candle Pattern RSI Divergence"""
    if len(df) < 50: return "없음"
    
    rsi = df['RSI'].values
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

def detect_liquidity_sweep(df):
    """Liquidity Sweep Detection"""
    if len(df) < 35: return "없음"
    curr = df.iloc[-1]
    prev_high = df.iloc[-30:-1]['high'].max()
    prev_low = df.iloc[-30:-1]['low'].min()
    
    if curr['high'] > prev_high and curr['close'] < prev_high:
        return f"고점 휩소 (Bearish Sweep at {prev_high:.0f})"
    if curr['low'] < prev_low and curr['close'] > prev_low:
        return f"저점 휩소 (Bullish Sweep at {prev_low:.0f})"
    return "없음"

def detect_cvd_divergence(df, lookback=30):
    """[Original] CVD Divergence with Swing Points"""
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
    """[Original] SMC Order Block & FVG (With Mitigation Logic)"""
    if len(df) < 50: return "식별 불가"
    
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
                fvgs.append({'type': 'BuFVG', 'top': float(low[i]), 'bottom': float(high[i-2]), 'mitigated': False})
        
        if high[i] < low[i-2]:
            gap = low[i-2] - high[i]
            if gap > (high[i] - low[i]) * 0.1:
                fvgs.append({'type': 'BeFVG', 'top': float(low[i-2]), 'bottom': float(high[i]), 'mitigated': False})
        
        # Order Block 생성 (Volume Filter)
        lookback = 20
        local_high = np.max(high[i-lookback:i]) if i > lookback else high[i-1]
        local_low = np.min(low[i-lookback:i]) if i > lookback else low[i-1]
        
        # Bullish OB
        if close[i] > open_p[i] and close[i-1] < open_p[i-1]: 
             if close[i] > local_high and volume[i] > vol_sma[i] * 1.5:
                obs.append({'type': 'BuOB', 'top': float(open_p[i-1]), 'bottom': float(low[i-1]), 'mitigated': False})
                    
        # Bearish OB
        if close[i] < open_p[i] and close[i-1] > open_p[i-1]: 
            if close[i] < local_low and volume[i] > vol_sma[i] * 1.5:
                obs.append({'type': 'BeOB', 'top': float(high[i-1]), 'bottom': float(open_p[i-1]), 'mitigated': False})
    
    # 살아있는(Unmitigated) 구조물만 반환
    live_obs = [ob for ob in obs if not ob['mitigated']][-2:]
    live_fvgs = [fvg for fvg in fvgs if not fvg['mitigated']][-2:]
    
    result = []
    for o in live_obs:
        o_type = "Bullish OB" if o['type'] == 'BuOB' else "Bearish OB"
        result.append(f"{o_type}({o['bottom']:.0f}-{o['top']:.0f})")
    for f in live_fvgs:
        f_type = "BullFVG" if f['type'] == 'BuFVG' else "BearFVG"
        result.append(f"{f_type}({f['bottom']:.0f}-{f['top']:.0f})")
        
    return " / ".join(result) if result else "주요 구조물 없음(All Mitigated)"

def analyze_data_advanced(df):
    try:
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx is not None:
             df['ADX'] = adx['ADX_14']
        else:
             df['ADX'] = 0
        df['VWAP'] = calculate_vwap(df)
        df['EMA200'] = ta.ema(df['close'], length=200)
    except:
        pass
    
    vp = calculate_volume_profile(df)
    rsi_div = detect_rsi_divergence(df)
    cvd_div = detect_cvd_divergence(df)
    smc_str = detect_smc_structure(df)
    lq_sweep = detect_liquidity_sweep(df)
    
    # CVD Slope
    cvd_slope = 0
    if len(df) >= 50:
        y = df['cvd'].tail(50).values
        x = np.arange(len(y))
        cvd_slope = np.polyfit(x, y, 1)[0]
    
    latest = df.iloc[-1]
    
    return {
        'close': float(latest['close']),
        'rsi': float(latest['RSI']) if not pd.isna(latest['RSI']) else 50,
        'atr': float(latest['ATR']) if not pd.isna(latest['ATR']) else 0,
        'adx': float(latest['ADX']) if not pd.isna(latest['ADX']) else 0,
        'vwap': float(latest['VWAP']),
        'vp': vp,
        'rsi_div': rsi_div,
        'cvd_div': cvd_div,
        'cvd_slope': cvd_slope,
        'smc': smc_str,
        'lq_sweep': lq_sweep
    }

def fetch_market_info():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    try:
        funding = exchange.fetch_funding_rate(SYMBOL)
        fr = funding['fundingRate'] * 100 if funding else 0
        oi_res = exchange.fapiPublicGetOpenInterest({'symbol': SYMBOL.replace('/', '')})
        oi = float(oi_res['openInterest']) if oi_res else 0
        return fr, oi
    except:
        return 0, 0

# 4. Gemini AI 전략 생성 (최적 모델 + 고급 데이터)
def get_ai_strategy():
    print("[INFO] Generating AI Prompt...")
    
    fr, oi = fetch_market_info()
    prompt = f"""
    당신은 'QuantAI'라는 비트코인 전문 퀀트 트레이더입니다. 
    다음의 **기관급 기술적 분석 데이터(SMC, CVD, Vol Profile, Liquidity Sweep)**를 바탕으로 **반드시 한국어(Korean)로만** 리포트를 작성하세요.
    
    [실시간 시장 데이터]
    - 펀딩비: {fr:.4f}% ({'롱 스퀴즈 주의' if fr > 0.02 else '숏 스퀴즈 주의' if fr < -0.02 else '중립'})
    - 미결제약정(OI): {oi:,.0f}
    """
    
    latest_price = 0
    
    for tf in TIMEFRAMES:
        df = fetch_data(tf)
        if df.empty: continue
        res = analyze_data_advanced(df)
        latest_price = res['close']
        
        prompt += f"""
        [{tf} 타임프레임 데이터]
        - 현재가: {res['close']:.2f}
        - VWAP (기관 평단): {res['vwap']:.2f}
        - 매물대(POC): {res['vp']['poc']:.2f} (Value Area: {res['vp']['val']:.2f} ~ {res['vp']['vah']:.2f})
        - 휩소(Sweep): {res['lq_sweep']}
        - 추세 강도 (ADX): {res['adx']:.2f} (25 이상이면 강한 추세)
        - RSI (14): {res['rsi']:.2f} -> 다이버전스: {res['rsi_div']}
        - CVD (고래 흐름): {res['cvd_div']} (Slope: {res['cvd_slope']:.2f})
        - SMC 구조(OB/FVG): {res['smc']}
        """

    prompt += f"""
    [전략 수립 지시사항]
    1. **Entry Strategy (Limit Order Focus)**: 실시간 '현재가'에 무조건 진입하지 마세요. 분석된 **Order Block(OB)이나 FVG의 입구 또는 0.5 레벨(중간값)**까지 가격이 도달할 때까지 기다리는 **지정가 진입(Limit Entry)** 전략을 우선적으로 고려하세요.
    2. **Safe Stop Loss (Sweep Resistance)**: 손절가를 단순히 OB/FVG 끝단에 붙이지 마세요. 세력의 유동성 탈취(Liquidity Sweep)를 견딜 수 있도록 **ATR 변동성의 0.5~1배 버퍼**를 더하거나, **직전 스윙 고점/저점(Swing Point)** 너머에 안전하게 설정하세요.
    3. **Trade Management**: 진입 후 목표가 도달 전이라도 구조적 변화(MSS)가 생기면 본절 이동이나 익절 대응 시나리오를 자율적으로 제시하세요.
    4. **Exit Strategy Selection**: 시장 상황(Trend vs Range)에 따라 적절한 출구 전략을 선택하세요. 강한 추세장에서는 **Trailing Stop**(수익 극대화)을, 박스권이나 역추세 매매에서는 **Hit & Run**(빠른 익절)을 권장합니다.

    [작성 양식]
    1. **시장 분석 (3줄 요약)**: 
       - 유동성 스윕(Sweep)과 매물대(POC/Value Area)를 활용해 현재 위치를 분석하세요.
       - 고래의 매집/매도(CVD) 흔적이 가격 변동과 일치하는지 확인하세요. (Slope 언급)
       
    2. **매매 전략 (택1)**: 
       - [롱(LONG) / 숏(SHORT) / 관망(WAIT)] 중 하나를 명확히 선택하세요.
       
    3. **진입/청산 가이드 (구체적 가격)**:
       - 진입가: 현재 추격매수 금지. 주요 지지/저항(POC, VAH/VAL)에 도달할 때까지 기다리는 지정가(Limit)를 제시하세요.
       - 목표가(TP): 1차, 2차 목표가
       - 손절가(SL): 전저점이나 주요 지지선 이탈 시 가격
       
    4. **핵심 근거**: 
       - 기술적 근거(SMC, CVD, RSI 등)를 2가지 이상 명확하게 드세요.
    
    **출력 형식:** 
    - 영어 사용을 지양하고, 전문가스러운 한국어 어조를 사용하세요.
    - 제목은 '##' 없이 1., 2. 번호로만 시작하세요.
    """
    
    print("[INFO] Sending to Gemini...")
    try:
        # 최신 라이브러리 사용
        # 모델은 gemini-exp-1206 (실험용, 쿼터 회피)
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return response.text, latest_price
    except Exception as e:
        return f"AI 에러: {e}", latest_price

# 5. HTML 생성
def generate_html(strategy_text, price):
    print("[INFO] Generating HTML...")
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuantAI Signal | BTC/USDT</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Inter', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            background: #0a0e1a;
            color: #e2e8f0;
            min-height: 100vh;
        }}

        /* 상단 헤더 */
        .header {{
            background: linear-gradient(135deg, #0d1117 0%, #161b27 100%);
            border-bottom: 1px solid #1e2d45;
            padding: 14px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .header-logo {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .header-logo .dot {{
            width: 10px;
            height: 10px;
            background: #00d4aa;
            border-radius: 50%;
            box-shadow: 0 0 8px #00d4aaaa;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.5; transform: scale(1.3); }}
        }}
        .header-logo span {{
            font-size: 1.1rem;
            font-weight: 700;
            color: #fff;
            letter-spacing: 0.05em;
        }}
        .header-logo span em {{
            font-style: normal;
            color: #4facfe;
        }}
        .header-status {{
            font-size: 0.75rem;
            color: #00d4aa;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .header-status::before {{
            content: '';
            display: inline-block;
            width: 7px;
            height: 7px;
            background: #00d4aa;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }}

        /* 메인 레이아웃 */
        .main-layout {{
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 0;
            height: calc(100vh - 53px);
        }}

        /* 왼쪽: 차트 영역 */
        .chart-panel {{
            background: #0d1117;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #1e2d45;
        }}
        .chart-top-bar {{
            padding: 12px 20px;
            border-bottom: 1px solid #1e2d45;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #0d1117;
        }}
        .chart-top-bar-left {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .chart-symbol {{
            font-size: 1rem;
            font-weight: 600;
            color: #fff;
        }}
        .chart-interval-badge {{
            background: #1e3a5f;
            color: #4facfe;
            font-size: 0.72rem;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 20px;
            border: 1px solid #2a5298;
            letter-spacing: 0.05em;
        }}
        .chart-current-price {{
            font-size: 1.4rem;
            font-weight: 700;
            color: #fff;
            transition: color 0.3s;
        }}
        .chart-price-change {{
            font-size: 0.8rem;
            font-weight: 500;
            margin-left: 8px;
        }}
        .price-up {{ color: #26a69a; }}
        .price-down {{ color: #ef5350; }}

        /* 차트 컨테이너 */
        #chart-container {{
            flex: 1;
            position: relative;
            overflow: hidden;
        }}
        #main-chart {{
            width: 100%;
            height: 68%;
        }}
        #volume-chart {{
            width: 100%;
            height: 32%;
            border-top: 1px solid #1e2d45;
        }}

        /* 거래 정보 바 */
        .market-info-bar {{
            padding: 8px 20px;
            background: #0d1117;
            border-top: 1px solid #1e2d45;
            display: flex;
            gap: 24px;
            font-size: 0.72rem;
            color: #64748b;
        }}
        .market-info-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .market-info-item label {{
            color: #475569;
        }}
        .market-info-item span {{
            color: #94a3b8;
            font-weight: 500;
        }}
        #ohlc-display {{
            display: flex;
            gap: 16px;
            font-size: 0.72rem;
        }}
        .ohlc-item label {{ color: #475569; margin-right: 4px; }}
        .ohlc-o {{ color: #94a3b8; }}
        .ohlc-h {{ color: #26a69a; }}
        .ohlc-l {{ color: #ef5350; }}
        .ohlc-c {{ color: #4facfe; }}

        /* 오른쪽: AI 리포트 패널 */
        .report-panel {{
            background: #0d1117;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .report-header {{
            padding: 16px 20px 12px;
            border-bottom: 1px solid #1e2d45;
        }}
        .report-title {{
            font-size: 0.85rem;
            font-weight: 600;
            color: #94a3b8;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        .report-generated {{
            font-size: 0.72rem;
            color: #475569;
            margin-top: 4px;
        }}
        .report-price-block {{
            padding: 14px 20px;
            border-bottom: 1px solid #1e2d45;
            background: linear-gradient(135deg, #0f1e35 0%, #0d1b2e 100%);
        }}
        .report-price-label {{
            font-size: 0.7rem;
            color: #475569;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .report-price-value {{
            font-size: 2rem;
            font-weight: 700;
            color: #fff;
            letter-spacing: -0.02em;
        }}
        .report-price-unit {{
            font-size: 0.9rem;
            color: #64748b;
            font-weight: 400;
            margin-left: 4px;
        }}
        .report-content {{
            flex: 1;
            overflow-y: auto;
            padding: 16px 20px;
            scrollbar-width: thin;
            scrollbar-color: #1e2d45 transparent;
        }}
        .report-content::-webkit-scrollbar {{
            width: 4px;
        }}
        .report-content::-webkit-scrollbar-thumb {{
            background: #1e2d45;
            border-radius: 2px;
        }}
        .report-text {{
            font-size: 0.82rem;
            line-height: 1.75;
            color: #94a3b8;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .report-text strong {{
            color: #e2e8f0;
        }}
        .report-footer {{
            padding: 10px 20px;
            border-top: 1px solid #1e2d45;
            font-size: 0.65rem;
            color: #334155;
            text-align: center;
            line-height: 1.5;
        }}

        /* 연결 상태 토스트 */
        #ws-toast {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #1e2d45;
            color: #94a3b8;
            padding: 8px 18px;
            border-radius: 20px;
            font-size: 0.75rem;
            border: 1px solid #2a3f5f;
            opacity: 0;
            transition: opacity 0.4s;
            z-index: 999;
            pointer-events: none;
        }}
        #ws-toast.show {{ opacity: 1; }}

        /* 반응형 */
        @media (max-width: 900px) {{
            .main-layout {{
                grid-template-columns: 1fr;
                grid-template-rows: 55vh 1fr;
                height: auto;
            }}
            .chart-panel {{
                border-right: none;
                border-bottom: 1px solid #1e2d45;
                height: 55vh;
            }}
            .report-panel {{
                height: auto;
                max-height: 60vh;
            }}
        }}
    </style>
</head>
<body>

<!-- 상단 헤더 -->
<header class="header">
    <div class="header-logo">
        <div class="dot"></div>
        <span>Quant<em>AI</em></span>
    </div>
    <div class="header-status" id="ws-status">WebSocket 연결 중...</div>
</header>

<!-- 메인 레이아웃 -->
<div class="main-layout">

    <!-- 왼쪽: 실시간 차트 -->
    <div class="chart-panel">
        <div class="chart-top-bar">
            <div class="chart-top-bar-left">
                <span class="chart-symbol">BTC / USDT</span>
                <span class="chart-interval-badge">5분봉</span>
            </div>
            <div>
                <span class="chart-current-price" id="live-price">--</span>
                <span class="chart-price-change" id="live-change"></span>
            </div>
        </div>

        <div id="chart-container">
            <div id="main-chart"></div>
            <div id="volume-chart"></div>
        </div>

        <div class="market-info-bar">
            <div id="ohlc-display">
                <span class="ohlc-item"><label>O</label><span class="ohlc-o" id="ohlc-o">--</span></span>
                <span class="ohlc-item"><label>H</label><span class="ohlc-h" id="ohlc-h">--</span></span>
                <span class="ohlc-item"><label>L</label><span class="ohlc-l" id="ohlc-l">--</span></span>
                <span class="ohlc-item"><label>C</label><span class="ohlc-c" id="ohlc-c">--</span></span>
            </div>
            <div class="market-info-item">
                <label>Vol</label>
                <span id="ohlc-vol">--</span>
            </div>
            <div class="market-info-item">
                <label>업데이트</label>
                <span id="last-update">--</span>
            </div>
        </div>
    </div>

    <!-- 오른쪽: AI 분석 리포트 -->
    <div class="report-panel">
        <div class="report-header">
            <div class="report-title">AI 분석 리포트</div>
            <div class="report-generated">생성 시각: {generated_at}</div>
        </div>
        <div class="report-price-block">
            <div class="report-price-label">분석 기준가</div>
            <div class="report-price-value">
                ${price:,.0f}<span class="report-price-unit">USDT</span>
            </div>
        </div>
        <div class="report-content">
            <div class="report-text" id="report-body">{strategy_text}</div>
        </div>
        <div class="report-footer">
            본 정보는 투자를 권유하지 않으며, 모든 투자 판단과 결과에 대한 책임은 본인에게 있습니다.
        </div>
    </div>

</div>

<!-- WebSocket 토스트 -->
<div id="ws-toast"></div>

<script>
(function() {{
    // ─── 차트 초기화 ───────────────────────────────────────
    const CHART_BG     = '#0d1117';
    const GRID_COLOR   = '#131c2e';
    const TEXT_COLOR   = '#64748b';
    const UP_COLOR     = '#26a69a';
    const DOWN_COLOR   = '#ef5350';
    const WICK_UP      = '#26a69a';
    const WICK_DOWN    = '#ef5350';
    const EMA20_COLOR  = '#f59e0b';
    const EMA50_COLOR  = '#a78bfa';

    const mainEl   = document.getElementById('main-chart');
    const volEl    = document.getElementById('volume-chart');
    const contEl   = document.getElementById('chart-container');

    function getHeights() {{
        var total = contEl.clientHeight;
        return {{ main: Math.floor(total * 0.68), vol: Math.floor(total * 0.32) }};
    }}

    var h = getHeights();
    mainEl.style.height = h.main + 'px';
    volEl.style.height  = h.vol  + 'px';

    // 메인 캔들 차트
    var mainChart = LightweightCharts.createChart(mainEl, {{
        width:  mainEl.clientWidth,
        height: h.main,
        layout: {{
            background: {{ color: CHART_BG }},
            textColor: TEXT_COLOR,
            fontSize: 11,
            fontFamily: "'Inter', 'Malgun Gothic', sans-serif"
        }},
        grid: {{
            vertLines: {{ color: GRID_COLOR }},
            horzLines: {{ color: GRID_COLOR }}
        }},
        crosshair: {{
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {{ color: '#334155', width: 1, style: 1 }},
            horzLine: {{ color: '#334155', width: 1, style: 1 }}
        }},
        rightPriceScale: {{
            borderColor: '#1e2d45',
            scaleMargins: {{ top: 0.08, bottom: 0.05 }}
        }},
        timeScale: {{
            borderColor: '#1e2d45',
            timeVisible: true,
            secondsVisible: false,
            rightOffset: 5
        }}
    }});

    var candleSeries = mainChart.addCandlestickSeries({{
        upColor:          UP_COLOR,
        downColor:        DOWN_COLOR,
        borderUpColor:    WICK_UP,
        borderDownColor:  WICK_DOWN,
        wickUpColor:      WICK_UP,
        wickDownColor:    WICK_DOWN
    }});

    var ema20Series = mainChart.addLineSeries({{
        color:     EMA20_COLOR,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: true,
        title: 'EMA20'
    }});

    var ema50Series = mainChart.addLineSeries({{
        color:     EMA50_COLOR,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: true,
        title: 'EMA50'
    }});

    // 볼륨 차트
    var volChart = LightweightCharts.createChart(volEl, {{
        width:  volEl.clientWidth,
        height: h.vol,
        layout: {{
            background: {{ color: CHART_BG }},
            textColor: TEXT_COLOR,
            fontSize: 10,
            fontFamily: "'Inter', 'Malgun Gothic', sans-serif"
        }},
        grid: {{
            vertLines: {{ color: GRID_COLOR }},
            horzLines: {{ color: GRID_COLOR }}
        }},
        rightPriceScale: {{
            borderColor: '#1e2d45',
            scaleMargins: {{ top: 0.05, bottom: 0 }}
        }},
        timeScale: {{
            borderColor: '#1e2d45',
            timeVisible: true,
            secondsVisible: false,
            visible: false
        }},
        crosshair: {{
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {{ color: '#334155', width: 1, style: 1, labelVisible: false }},
            horzLine: {{ visible: false }}
        }}
    }});

    var volSeries = volChart.addHistogramSeries({{
        priceFormat: {{ type: 'volume' }},
        priceScaleId: 'right'
    }});

    // 두 차트 시간축 동기화
    mainChart.timeScale().subscribeVisibleLogicalRangeChange(function(range) {{
        if (range) volChart.timeScale().setVisibleLogicalRange(range);
    }});
    volChart.timeScale().subscribeVisibleLogicalRangeChange(function(range) {{
        if (range) mainChart.timeScale().setVisibleLogicalRange(range);
    }});

    // 크로스헤어 동기화
    mainChart.subscribeCrosshairMove(function(param) {{
        if (!param || !param.time) return;
        volChart.setCrosshairPosition(0, param.time, volSeries);
        if (param.seriesData && param.seriesData.size > 0) {{
            var d = param.seriesData.get(candleSeries);
            if (d) {{
                document.getElementById('ohlc-o').textContent = formatPrice(d.open);
                document.getElementById('ohlc-h').textContent = formatPrice(d.high);
                document.getElementById('ohlc-l').textContent = formatPrice(d.low);
                document.getElementById('ohlc-c').textContent = formatPrice(d.close);
                var vd = param.seriesData.get(volSeries);
                if (vd) document.getElementById('ohlc-vol').textContent = formatVol(vd.value);
            }}
        }}
    }});

    // ─── 데이터 처리 유틸 ─────────────────────────────────
    function formatPrice(v) {{
        return v ? Number(v).toLocaleString('en-US', {{minimumFractionDigits:1, maximumFractionDigits:1}}) : '--';
    }}
    function formatVol(v) {{
        if (!v) return '--';
        if (v >= 1000) return (v/1000).toFixed(1) + 'K';
        return Number(v).toFixed(2);
    }}
    function toUTC(ts) {{ return Math.floor(ts / 1000); }}

    // EMA 계산 (지수이동평균)
    function calcEMA(data, period) {{
        var result = [];
        var k = 2 / (period + 1);
        var ema = null;
        for (var i = 0; i < data.length; i++) {{
            var c = data[i].close;
            if (ema === null) {{
                if (i + 1 >= period) {{
                    var sum = 0;
                    for (var j = i - period + 1; j <= i; j++) sum += data[j].close;
                    ema = sum / period;
                    result.push({{ time: data[i].time, value: ema }});
                }}
            }} else {{
                ema = c * k + ema * (1 - k);
                result.push({{ time: data[i].time, value: ema }});
            }}
        }}
        return result;
    }}

    // ─── REST: 초기 캔들 로드 ─────────────────────────────
    var candles = [];
    var openDay = null;

    function loadInitialData() {{
        showToast('과거 데이터 불러오는 중...');
        fetch('https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=500')
            .then(function(r) {{ return r.json(); }})
            .then(function(raw) {{
                candles = [];
                var volData = [];
                for (var i = 0; i < raw.length; i++) {{
                    var k = raw[i];
                    var t = toUTC(parseInt(k[0]));
                    var c = {{
                        time:  t,
                        open:  parseFloat(k[1]),
                        high:  parseFloat(k[2]),
                        low:   parseFloat(k[3]),
                        close: parseFloat(k[4])
                    }};
                    candles.push(c);
                    volData.push({{
                        time:  t,
                        value: parseFloat(k[5]),
                        color: c.close >= c.open ? 'rgba(38,166,154,0.5)' : 'rgba(239,83,80,0.5)'
                    }});
                }}
                candleSeries.setData(candles);
                volSeries.setData(volData);

                var ema20 = calcEMA(candles, 20);
                var ema50 = calcEMA(candles, 50);
                ema20Series.setData(ema20);
                ema50Series.setData(ema50);

                mainChart.timeScale().fitContent();

                // 현재가 초기 표시
                if (candles.length > 0) {{
                    var last = candles[candles.length - 1];
                    updatePriceDisplay(last.close, last.open);
                    updateOHLC(last, volData[volData.length - 1].value);
                }}

                showToast('실시간 WebSocket 연결 중...', 2000);
                setTimeout(connectWebSocket, 500);
            }})
            .catch(function(e) {{
                console.error('초기 데이터 로드 실패:', e);
                showToast('데이터 로드 실패. 재시도 중...', 3000);
                setTimeout(loadInitialData, 5000);
            }});
    }}

    // ─── WebSocket 실시간 연결 ────────────────────────────
    var ws = null;
    var wsReconnectTimer = null;
    var lastVolData = {{}};

    function connectWebSocket() {{
        if (ws) ws.close();
        ws = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@kline_5m');

        ws.onopen = function() {{
            document.getElementById('ws-status').textContent = 'LIVE · 실시간 연결됨';
            showToast('✅ 실시간 5분봉 연결 완료!', 3000);
            if (wsReconnectTimer) {{ clearTimeout(wsReconnectTimer); wsReconnectTimer = null; }}
        }};

        ws.onmessage = function(event) {{
            var msg  = JSON.parse(event.data);
            var k    = msg.k;
            var t    = toUTC(k.t);
            var open  = parseFloat(k.o);
            var high  = parseFloat(k.h);
            var low   = parseFloat(k.l);
            var close = parseFloat(k.c);
            var vol   = parseFloat(k.v);

            var newCandle = {{ time: t, open: open, high: high, low: low, close: close }};
            candleSeries.update(newCandle);

            var volCandle = {{
                time:  t,
                value: vol,
                color: close >= open ? 'rgba(38,166,154,0.5)' : 'rgba(239,83,80,0.5)'
            }};
            volSeries.update(volCandle);
            lastVolData[t] = vol;

            // 캔들 배열 업데이트 (EMA 재계산)
            var lastIdx = candles.length - 1;
            if (lastIdx >= 0 && candles[lastIdx].time === t) {{
                candles[lastIdx] = newCandle;
            }} else {{
                candles.push(newCandle);
                if (candles.length > 600) candles.shift();
            }}

            // EMA 업데이트 (마지막 60개만 재계산해서 성능 최적화)
            var tailStart = Math.max(0, candles.length - 60);
            var tailCandles = candles.slice(tailStart);
            var ema20 = calcEMA(candles, 20).slice(-60);
            var ema50 = calcEMA(candles, 50).slice(-60);
            for (var i = 0; i < ema20.length; i++) ema20Series.update(ema20[i]);
            for (var i = 0; i < ema50.length; i++) ema50Series.update(ema50[i]);

            // UI 업데이트
            updatePriceDisplay(close, open);
            updateOHLC(newCandle, vol);

            // 업데이트 시각
            var now = new Date();
            document.getElementById('last-update').textContent =
                now.getHours().toString().padStart(2,'0') + ':' +
                now.getMinutes().toString().padStart(2,'0') + ':' +
                now.getSeconds().toString().padStart(2,'0');
        }};

        ws.onerror = function(e) {{
            console.error('WebSocket 에러:', e);
        }};

        ws.onclose = function() {{
            document.getElementById('ws-status').textContent = '연결 끊김 · 재연결 중...';
            showToast('⚠️ 연결 끊김. 5초 후 재연결...', 4000);
            wsReconnectTimer = setTimeout(connectWebSocket, 5000);
        }};
    }}

    // ─── UI 업데이트 함수들 ───────────────────────────────
    var prevClose = null;

    function updatePriceDisplay(close, open) {{
        var el = document.getElementById('live-price');
        el.textContent = '$' + close.toLocaleString('en-US', {{minimumFractionDigits:1, maximumFractionDigits:1}});

        var isUp = prevClose === null ? close >= open : close >= prevClose;
        el.style.color = isUp ? '#26a69a' : '#ef5350';

        var dayOpen = candles.length > 0 ? candles[0].open : open;
        var pct = ((close - dayOpen) / dayOpen * 100);
        var chEl = document.getElementById('live-change');
        chEl.textContent = (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
        chEl.className = 'chart-price-change ' + (pct >= 0 ? 'price-up' : 'price-down');

        prevClose = close;
    }}

    function updateOHLC(c, vol) {{
        document.getElementById('ohlc-o').textContent = formatPrice(c.open);
        document.getElementById('ohlc-h').textContent = formatPrice(c.high);
        document.getElementById('ohlc-l').textContent = formatPrice(c.low);
        document.getElementById('ohlc-c').textContent = formatPrice(c.close);
        document.getElementById('ohlc-vol').textContent = formatVol(vol);
    }}

    function showToast(msg, duration) {{
        var t = document.getElementById('ws-toast');
        t.textContent = msg;
        t.classList.add('show');
        if (duration) setTimeout(function() {{ t.classList.remove('show'); }}, duration);
    }}

    // ─── 리사이즈 대응 ────────────────────────────────────
    window.addEventListener('resize', function() {{
        var nh = getHeights();
        mainChart.resize(mainEl.clientWidth, nh.main);
        volChart.resize(volEl.clientWidth, nh.vol);
        mainEl.style.height = nh.main + 'px';
        volEl.style.height  = nh.vol  + 'px';
    }});

    // 시작
    loadInitialData();
}})();
</script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("[SUCCESS] index.html created.")

if __name__ == "__main__":
    strategy, price = get_ai_strategy()
    generate_html(strategy, price)
    print("[DONE] Analysis Cycle Complete.")