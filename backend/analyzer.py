import os
import sys
import json
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pandas_ta as ta
import ccxt
from dotenv import load_dotenv
from google import genai

# 경고 무시 및 인코딩 설정
warnings.filterwarnings("ignore")
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
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

def fetch_long_short_ratio():
    """바이낸스 선물 롱/숏 비율 데이터 수집"""
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    try:
        # 글로벌 롱/숏 계정 비율 (최근 5분)
        symbol = SYMBOL.replace('/', '')
        params = {'symbol': symbol, 'period': '5m', 'limit': 1}
        
        # CCXT 최신 버전에서는 fapiDataGetGlobalLongShortAccountRatio 사용
        resp = exchange.fapiDataGetGlobalLongShortAccountRatio(params)
            
        if resp and len(resp) > 0:
            data = resp[0]
            # longAccount: 롱 비율 (0.XX 형식), shortAccount: 숏 비율 (0.XX 형식)
            long_p = float(data['longAccount']) * 100
            short_p = float(data['shortAccount']) * 100
            return {"long": round(long_p, 1), "short": round(short_p, 1)}
    except Exception as e:
        print(f"[ERROR] Long/Short ratio failed: {e}")
    return {"long": 50.0, "short": 50.0}

def fetch_crypto_news():
    """최신 뉴스 수집"""
    return [
        "SEC 의장, 2026년 크립토 규제 아젠다 발표 - 제도권 편입 가속화",
        "미국 비트코인 현물 ETF, 어제 1.3억 달러 순유출 기록",
        "폴란드 대통령, EU 가상자산법(MiCA) 이행안에 거부권 행사",
        "홍콩, 3월 첫 스테이블코인 라이선스 발급 예정",
        "비트코인 L2 네트워크 활성 사용자 수 역대 최고치 경신"
    ]

# 파일 기반 캐시 (서버 재시작 대응)
BRIEF_CACHE_FILE = "brief_cache.json"

def fetch_ai_daily_brief():
    """AI 가 생성한 일일 뉴스 요약 (1시간 파일 캐시 적용)"""
    import json
    
    now = datetime.now()
    # 1. 파일 캐시 로드 시도
    if os.path.exists(BRIEF_CACHE_FILE):
        try:
            with open(BRIEF_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                expiry = datetime.fromisoformat(cache['expiry'])
                if expiry > now:
                    return cache['data']
        except:
            pass

    # 2. 새로운 브리핑 생성
    news = fetch_crypto_news()
    sentiment = fetch_long_short_ratio()
    events = get_economic_events()
    
    news_text = "\n".join([f"- {n}" for n in news])
    event_text = "\n".join([f"- {e['title']} ({e['d_day']})" for e in events])
    
    prompt = f"""
    당신은 'QuantAI'의 수석 분석가입니다. 다음 데이터를 종합하여 오늘 오전의 **비트코인 핵심 브리핑 3줄**을 작성하세요.
    - 한국어로 작성할 것
    - 마크다운 기호를 쓰지 말 것 (텍스트만 3줄)
    - 줄당 40자 이내로 핵심만 찌를 것
    
    [데이터]
    1. 뉴스: {news_text}
    2. 시장심리: 롱 {sentiment['long']}% vs 숏 {sentiment['short']}%
    3. 일정: {event_text}
    """
    try:
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        briefs = response.text.strip().split('\n')
        clean_briefs = [b.replace('*', '').replace('-', '').replace('•', '').strip() for b in briefs if b.strip()]
        result = clean_briefs[:3]
        
        if len(result) >= 1:
            # 파일 캐시 저장
            with open(BRIEF_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "data": result,
                    "expiry": (now + timedelta(hours=1)).isoformat()
                }, f, ensure_ascii=False)
            return result
        raise ValueError("Invalid AI Response")
    except Exception as e:
        print(f"[ERROR] AI Daily Briefing failed (Switching to fallback): {e}")
        return ["뉴스 요약을 불러올 수 없습니다.", "현재 시장 변동성에 유의하세요.", "주요 경제 일정을 확인하세요."]

def get_economic_events():
    """주요 거시경제 일정 데이터"""
    return [
        {"title": "미국 CPI(소비자물가지수) 발표", "d_day": "D-1", "impact": "High", "date": "2026-02-21"},
        {"title": "FOMC 정례 회의", "d_day": "D-4", "impact": "Critical", "date": "2026-02-24"},
        {"title": "홍콩 스테이블코인 라이선스 발표", "d_day": "D-10", "impact": "Medium", "date": "2026-03-02"}
    ]

def get_ai_strategy() -> dict:
    fr, oi = fetch_market_info()
    news = fetch_crypto_news()
    events = get_economic_events()

    news_str = "\n".join([f"- {n}" for n in news])
    event_str = "\n".join([f"- {e['title']} ({e['d_day']})" for e in events])

    prompt = f"""
    당신은 'QuantAI'라는 비트코인 전문 퀀트 트레이더입니다. 
    다음의 **기술적 분석**과 **실시간 뉴스/이벤트**를 결합하여 **반드시 한국어(Korean)**로 입체적인 리포트를 작성하세요.
    
    [실시간 시장 데이터]
    - 펀딩비: {fr:.4f}% | 미결제약정(OI): {oi:,.0f}
    
    [최신 주요 뉴스]
    {news_str}
    
    [예정된 주요 일정]
    {event_str}
    """
    
    latest_price = 0.0
    for tf in TIMEFRAMES:
        df = fetch_data(tf)
        if df.empty: continue
        res = analyze_data_advanced(df)
        latest_price = res['close']
        prompt += f"""
        [{tf} 타임프레임 데이터]
        - 현재가: {res['close']:.2f} | VWAP: {res['vwap']:.2f}
        - POC: {res['vp']['poc']:.2f} | 휩소: {res['lq_sweep']}
        - ADX: {res['adx']:.2f} | RSI: {res['rsi']:.2f} | SMC: {res['smc']}
        """

    prompt += """
    [전략 수립 지시사항]
    1. **Fundamental + Technical**: 기술적 분석뿐만 아니라 현재 뉴스(펀딩비 변화, 규제 이슈)가 시장 심리에 미치는 영향을 분석에 포함하세요.
    2. **Entry/Exit Strategy**: 뉴스 발표 전후의 변동성을 고려한 진입/손절가를 제시하세요.
    
    [작성 양식]
    1. **시장 종합 분석 (3줄 요약)**: 기술적 지표와 뉴스를 결합한 시황 분석
    2. **매매 전략**: [롱 / 숏 / 관망]
    3. **가이드 (가격)**: 진입가, 목표가, 손절가
    4. **핵심 근거**: (1) 기술적 근거 (2) 펀더멘탈(뉴스/이벤트) 근거
    
    [중요]
    리포트의 가장 마지막에 가상 매매 추적을 위해 다음 형식을 반드시 포함하세요. (숫자만 사용)
    SIGNAL_JSON:
    ```json
    {"side": "LONG" 또는 "SHORT" 또는 "NONE", "entry": 12345.6, "tp": 12345.6, "sl": 12345.6}
    ```
    """
    
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        strategy_text = response.text
    except Exception as e:
        strategy_text = f"AI 분석 오류: {e}"
    
    return {
        "price": latest_price,
        "strategy": strategy_text,
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "funding_rate": fr,
        "open_interest": oi,
        "news": news,
        "events": events
    }
