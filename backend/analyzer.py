import os
import sys
import warnings
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from google import genai
from dotenv import load_dotenv
from datetime import datetime

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

SYMBOL = 'BTC/USDT'
TIMEFRAMES = ['1h', '4h', '1d']
LIMIT = 500


def fetch_data(tf):
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    params = {'symbol': SYMBOL.replace('/', ''), 'interval': tf, 'limit': LIMIT}

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

        df['taker_sell_vol'] = df['volume'] - df['taker_buy_vol']
        df['delta'] = df['taker_buy_vol'] - df['taker_sell_vol']
        df['cvd'] = df['delta'].cumsum()

        return df
    except Exception as e:
        print(f"[ERROR] Fetch failed ({tf}): {e}")
        return pd.DataFrame()


def calculate_vwap(df):
    tp = (df['high'] + df['low'] + df['close']) / 3
    return (tp * df['volume']).cumsum() / df['volume'].cumsum()


def calculate_volume_profile(df):
    if len(df) < 50:
        return {'poc': 0, 'vah': 0, 'val': 0}
    price = df['close'].values
    volume = df['volume'].values
    hist, bin_edges = np.histogram(price, bins=100, weights=volume)
    max_idx = np.argmax(hist)
    poc = (bin_edges[max_idx] + bin_edges[max_idx + 1]) / 2

    total_vol = np.sum(hist)
    target_vol = total_vol * 0.7
    current_vol = hist[max_idx]
    lower_idx = max_idx
    upper_idx = max_idx

    while current_vol < target_vol:
        can_go_lower = lower_idx > 0
        can_go_upper = upper_idx < 99
        vol_lower = hist[lower_idx - 1] if can_go_lower else 0
        vol_upper = hist[upper_idx + 1] if can_go_upper else 0

        if not can_go_lower and not can_go_upper:
            break

        if vol_upper > vol_lower:
            upper_idx += 1
            current_vol += hist[upper_idx]
        else:
            lower_idx -= 1
            current_vol += hist[lower_idx]

    return {
        'poc': float(poc),
        'vah': float(bin_edges[upper_idx + 1]),
        'val': float(bin_edges[lower_idx])
    }


def detect_rsi_divergence(df):
    if len(df) < 50:
        return "없음"

    rsi = df['RSI'].values
    high = df['high'].values
    low = df['low'].values

    peaks = []
    troughs = []

    for i in range(len(df) - 50, len(df)):
        if i < 2:
            continue
        if rsi[i - 2] <= rsi[i - 1] and rsi[i - 1] > rsi[i]:
            peaks.append((i - 1, rsi[i - 1], high[i - 1]))
        if rsi[i - 2] >= rsi[i - 1] and rsi[i - 1] < rsi[i]:
            troughs.append((i - 1, rsi[i - 1], low[i - 1]))

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
    if len(df) < 35:
        return "없음"
    curr = df.iloc[-1]
    prev_high = df.iloc[-30:-1]['high'].max()
    prev_low = df.iloc[-30:-1]['low'].min()

    if curr['high'] > prev_high and curr['close'] < prev_high:
        return f"고점 휩소 (Bearish Sweep at {prev_high:.0f})"
    if curr['low'] < prev_low and curr['close'] > prev_low:
        return f"저점 휩소 (Bullish Sweep at {prev_low:.0f})"
    return "없음"


def detect_cvd_divergence(df, lookback=30):
    if len(df) < lookback:
        return "없음"

    close = df['close'].values
    cvd = df['cvd'].values

    subset_close = close[-lookback:]
    subset_cvd = cvd[-lookback:]

    price_min_idx = np.argmin(subset_close)
    price_max_idx = np.argmax(subset_close)
    cvd_min_idx = np.argmin(subset_cvd)
    cvd_max_idx = np.argmax(subset_cvd)

    if (price_min_idx > cvd_min_idx
            and subset_close[price_min_idx] < subset_close[cvd_min_idx]
            and subset_cvd[price_min_idx] > subset_cvd[cvd_min_idx]):
        return "강력 상승 다이버전스 (CVD Bullish Div - 매도 흡수)"

    if (price_max_idx > cvd_max_idx
            and subset_close[price_max_idx] > subset_close[cvd_max_idx]
            and subset_cvd[price_max_idx] < subset_cvd[cvd_max_idx]):
        return "강력 하락 다이버전스 (CVD Bearish Div - 매수 흡수)"

    return "없음"


def detect_smc_structure(df):
    if len(df) < 50:
        return "식별 불가"

    obs = []
    fvgs = []

    open_p = df['open'].values
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    volume = df['volume'].values
    vol_sma = df['volume'].rolling(20).mean().fillna(0).values

    for i in range(2, len(df)):
        curr_low = low[i]
        curr_high = high[i]

        for ob in obs:
            if ob['mitigated']:
                continue
            if ob['type'] == 'BuOB' and curr_low <= ob['top']:
                ob['mitigated'] = True
            elif ob['type'] == 'BeOB' and curr_high >= ob['bottom']:
                ob['mitigated'] = True

        for fvg in fvgs:
            if fvg['mitigated']:
                continue
            if fvg['type'] == 'BuFVG' and curr_low <= fvg['top']:
                fvg['mitigated'] = True
            elif fvg['type'] == 'BeFVG' and curr_high >= fvg['bottom']:
                fvg['mitigated'] = True

        if low[i] > high[i - 2]:
            gap = low[i] - high[i - 2]
            if gap > (high[i] - low[i]) * 0.1:
                fvgs.append({'type': 'BuFVG', 'top': float(low[i]), 'bottom': float(high[i - 2]), 'mitigated': False})

        if high[i] < low[i - 2]:
            gap = low[i - 2] - high[i]
            if gap > (high[i] - low[i]) * 0.1:
                fvgs.append({'type': 'BeFVG', 'top': float(low[i - 2]), 'bottom': float(high[i]), 'mitigated': False})

        lookback = 20
        local_high = np.max(high[i - lookback:i]) if i > lookback else high[i - 1]
        local_low = np.min(low[i - lookback:i]) if i > lookback else low[i - 1]

        if close[i] > open_p[i] and close[i - 1] < open_p[i - 1]:
            if close[i] > local_high and volume[i] > vol_sma[i] * 1.5:
                obs.append({'type': 'BuOB', 'top': float(open_p[i - 1]), 'bottom': float(low[i - 1]), 'mitigated': False})

        if close[i] < open_p[i] and close[i - 1] > open_p[i - 1]:
            if close[i] < local_low and volume[i] > vol_sma[i] * 1.5:
                obs.append({'type': 'BeOB', 'top': float(high[i - 1]), 'bottom': float(open_p[i - 1]), 'mitigated': False})

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
    except Exception:
        pass

    vp = calculate_volume_profile(df)
    rsi_div = detect_rsi_divergence(df)
    cvd_div = detect_cvd_divergence(df)
    smc_str = detect_smc_structure(df)
    lq_sweep = detect_liquidity_sweep(df)

    cvd_slope = 0
    if len(df) >= 50:
        y = df['cvd'].tail(50).values
        x = np.arange(len(y))
        cvd_slope = float(np.polyfit(x, y, 1)[0])

    latest = df.iloc[-1]

    return {
        'close': float(latest['close']),
        'rsi': float(latest['RSI']) if not pd.isna(latest['RSI']) else 50.0,
        'atr': float(latest['ATR']) if not pd.isna(latest['ATR']) else 0.0,
        'adx': float(latest['ADX']) if not pd.isna(latest['ADX']) else 0.0,
        'vwap': float(latest['VWAP']),
        'vp': vp,
        'rsi_div': rsi_div,
        'cvd_div': cvd_div,
        'cvd_slope': cvd_slope,
        'smc': smc_str,
        'lq_sweep': lq_sweep,
    }


def fetch_market_info():
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    try:
        funding = exchange.fetch_funding_rate(SYMBOL)
        fr = funding['fundingRate'] * 100 if funding else 0
        oi_res = exchange.fapiPublicGetOpenInterest({'symbol': SYMBOL.replace('/', '')})
        oi = float(oi_res['openInterest']) if oi_res else 0
        return float(fr), float(oi)
    except Exception:
        return 0.0, 0.0


def get_ai_strategy() -> dict:
    """
    AI 전략 분석을 실행하고 JSON 직렬화 가능한 dict를 반환합니다.
    """
    fr, oi = fetch_market_info()

    prompt = f"""
    당신은 'QuantAI'라는 비트코인 전문 퀀트 트레이더입니다.
    다음의 **기관급 기술적 분석 데이터(SMC, CVD, Vol Profile, Liquidity Sweep)**를 바탕으로 **반드시 한국어(Korean)로만** 리포트를 작성하세요.

    [실시간 시장 데이터]
    - 펀딩비: {fr:.4f}% ({'롱 스퀴즈 주의' if fr > 0.02 else '숏 스퀴즈 주의' if fr < -0.02 else '중립'})
    - 미결제약정(OI): {oi:,.0f}
    """

    latest_price = 0.0

    for tf in TIMEFRAMES:
        df = fetch_data(tf)
        if df.empty:
            continue
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

    prompt += """
    [전략 수립 지시사항]
    1. **Entry Strategy (Limit Order Focus)**: Order Block(OB)이나 FVG의 0.5 레벨까지 기다리는 지정가 진입(Limit Entry)을 우선 고려하세요.
    2. **Safe Stop Loss (Sweep Resistance)**: ATR 변동성의 0.5~1배 버퍼를 더하거나 직전 스윙 고점/저점 너머에 안전하게 설정하세요.
    3. **Trade Management**: 구조적 변화(MSS)가 생기면 본절 이동이나 익절 대응 시나리오를 제시하세요.
    4. **Exit Strategy Selection**: 강한 추세장에서는 Trailing Stop을, 박스권이나 역추세 매매에서는 Hit & Run을 권장합니다.

    [작성 양식]
    1. **시장 분석 (3줄 요약)**
    2. **매매 전략 (택1)**: [롱(LONG) / 숏(SHORT) / 관망(WAIT)]
    3. **진입/청산 가이드 (구체적 가격)**: 진입가, 목표가(TP1, TP2), 손절가(SL)
    4. **핵심 근거**: 기술적 근거 2가지 이상

    **출력 형식:** 영어 사용을 지양하고, 전문가스러운 한국어 어조를 사용하세요. 제목은 1., 2. 번호로만 시작하세요.
    """

    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        strategy_text = response.text
    except Exception as e:
        strategy_text = f"AI 분석 오류: {e}"

    return {
        "price": latest_price,
        "strategy": strategy_text,
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "funding_rate": fr,
        "open_interest": oi,
    }
