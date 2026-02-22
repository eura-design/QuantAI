import os
import sys
import json
import warnings
import re
import threading
from datetime import datetime, timedelta

import pandas as pd
import pandas_ta as ta
import requests
import feedparser
from dotenv import load_dotenv
from google import genai
from core.fetcher import MarketDataFetcher
from core.indicators import (
    calculate_vwap, calculate_volume_profile, detect_divergences, 
    detect_smc_structure, detect_liquidity_sweep
)

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

# 글로벌 락 및 인 메모리 캐시 (동시 요청 방지)
_locks = {
    "news": threading.Lock(),
    "brief": threading.Lock(),
    "strategy": threading.Lock()
}
_mem_cache = {}

def get_from_mem(key):
    val = _mem_cache.get(key)
    if val and val['expiry'] > datetime.now():
        return val['data']
    return None

def set_to_mem(key, data, minutes=5):
    _mem_cache[key] = {
        "data": data,
        "expiry": datetime.now() + timedelta(minutes=minutes)
    }

fetcher = MarketDataFetcher(SYMBOL)

def fetch_data(tf):
    """OHLCV 데이터 수집 (Core Fetcher 사용)"""
    return fetcher.fetch_ohlcv(tf, LIMIT)

def analyze_data_advanced(df):
    """고급 기술 분석 (Core Indicators 사용)"""
    if df.empty: return {}
    
    df = df.copy()
    # 기본 지표 계산 (core에서 공통으로 쓰지 않는 파생 지표들)
    try:
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        adx_res = ta.adx(df['high'], df['low'], df['close'], length=14)
        df['adx'] = adx_res['ADX_14'] if adx_res is not None else 0
        df['vwap'] = calculate_vwap(df)
        df['cvd'] = df['delta'].cumsum()
    except Exception: pass

    # Core 분석 엔진 호출
    vp = calculate_volume_profile(df)
    cvd_div, rsi_div = detect_divergences(df)
    fvgs, obs = detect_smc_structure(df)
    lq_sweep = detect_liquidity_sweep(df)

    # 기존 UI/API 호환을 위한 SMC 텍스트 포맷팅
    smc_res = []
    for o in obs:
        o_type = "Bullish OB" if o['type'] == 'BullOB' else "Bearish OB"
        smc_res.append(f"{o_type}({o['bottom']:.0f}-{o['top']:.0f})")
    for f in fvgs:
        f_type = "BullFVG" if f['type'] == 'BullFVG' else "BearFVG"
        smc_res.append(f"{f_type}({f['bottom']:.0f}-{f['top']:.0f})")
    smc_str = " / ".join(smc_res) if smc_res else "주요 구조물 없음(All Mitigated)"

    latest = df.iloc[-1]
    return {
        'close': float(latest['close']),
        'rsi': float(latest['rsi']) if not pd.isna(latest['rsi']) else 50.0,
        'atr': float(latest['atr']) if not pd.isna(latest['atr']) else 0.0,
        'adx': float(latest['adx']) if not pd.isna(latest['adx']) else 0.0,
        'vwap': float(latest['vwap']),
        'vp': vp,
        'rsi_div': rsi_div,
        'cvd_div': cvd_div,
        'smc': smc_str,
        'lq_sweep': lq_sweep,
    }

def fetch_market_info():
    """시장 컨텍스트 수집 (Core Fetcher 사용)"""
    return fetcher.fetch_market_context()

def fetch_long_short_ratio():
    """바이낸스 선물 롱/숏 비율 데이터 수집"""
    symbol = SYMBOL.replace('/', '')
    periods = ['5m', '15m', '1h']
    endpoints = [
        "https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
        "https://fapi.binance.com/futures/data/topLongShortAccountRatio"
    ]
    
    for url in endpoints:
        for pd in periods:
            try:
                params = {'symbol': symbol, 'period': pd, 'limit': 1}
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data_list = response.json()
                    if data_list:
                        data = data_list[0]
                        l = float(data.get('longAccount', 0))
                        s = float(data.get('shortAccount', 0))
                        if l+s > 0:
                            return {"long": round(l/(l+s)*100, 1), "short": round(s/(l+s)*100, 1)}
            except: continue
    return {"long": 51.4, "short": 48.6}

def fetch_crypto_news(lang='ko', translate=True):
    """실시간 뉴스 수집 (중복 요청 방지 및 최적화)"""
    now = datetime.now()
    cache_key = f"news_{lang}_{translate}"
    
    # 1. 인 메모리 캐시 확인
    m_cache = get_from_mem(cache_key)
    if m_cache: return m_cache

    # 2. 파일 캐시 확인
    cache_file = f"news_cache_{lang}_{translate}.json"
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                c = json.load(f)
                if datetime.fromisoformat(c['expiry']) > now:
                    return c['data']
        except: pass

    # 3. 데이터 갱신 (락 사용)
    with _locks["news"]:
        # 락 대기 중 다른 스레드가 먼저 갱신했을 수 있으므로 다시 확인
        m_cache = get_from_mem(cache_key)
        if m_cache: return m_cache
        
        try:
            feed = feedparser.parse("https://www.coindesk.com/arc/outboundfeeds/rss/")
            raw_news = [e.title for e in feed.entries[:5]]
            if not raw_news: raise ValueError("No news")
            
            final_news = raw_news
            if lang == 'ko' and translate:
                try:
                    res = client.models.generate_content(
                        model='gemini-flash-latest', 
                        contents=f"Translate and summarize these 5 Bitcoin news titles into concise Korean (one line per news):\n{chr(10).join(raw_news)}"
                    )
                    translated = [line.strip().replace('*','').replace('-','').strip() for line in res.text.strip().split('\n') if line.strip()]
                    final_news = translated[:5] if len(translated) >= 3 else raw_news
                except Exception as e:
                    print(f"[DEBUG] News Translation Fail: {e}")
                    final_news = raw_news # 폴백
            
            # 결과 저장
            set_to_mem(cache_key, final_news, minutes=60)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({"data": final_news, "expiry": (now + timedelta(hours=1)).isoformat()}, f, ensure_ascii=False)
            return final_news
        except Exception as e:
            print(f"[ERROR] News fetch failed: {e}")
            return []

def fetch_ai_daily_brief(lang='ko'):
    """AI 뉴스 요약 (중복 요청 방지 및 최적화)"""
    now = datetime.now()
    cache_key = f"brief_{lang}"
    m_cache = get_from_mem(cache_key)
    if m_cache: return m_cache

    cache_file = f"brief_cache_{lang}.json"
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                c = json.load(f)
                if datetime.fromisoformat(c['expiry']) > now: return c['data']
        except: pass

    with _locks["brief"]:
        m_cache = get_from_mem(cache_key)
        if m_cache: return m_cache

        # 번역되지 않은 영문 뉴스를 사용하여 AI 처리 비용 절감
        news = fetch_crypto_news(lang='en', translate=False)
        sentiment = fetch_long_short_ratio()
        events = get_economic_events(lang=lang)
        
        prompt = (
            f"Write a 3-line Bitcoin briefing in {'Korean' if lang=='ko' else 'English'}. "
            f"Input News: {news}. Sentiment: L {sentiment['long']}% vs S {sentiment['short']}%. Events: {events}. "
            "Keep it under 40 chars per line, plain text only."
        )

        try:
            res = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
            result = [b.replace('*','').replace('-','').strip() for b in res.text.strip().split('\n') if b.strip()][:3]
            if not result: result = ["시장 분석 데이터를 불러올 수 없습니다."] if lang=='ko' else ["Could not load briefing."]
            
            set_to_mem(cache_key, result, minutes=60)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({"data": result, "expiry": (now + timedelta(hours=1)).isoformat()}, f, ensure_ascii=False)
            return result
        except Exception as e:
            print(f"[ERROR] Briefing failed: {e}")
            return []

def get_economic_events(lang='ko'):
    """경제 일정 (하드코딩된 데이터 기반)"""
    today = datetime.now().date()
    raw = [
        {"ko": "미국 CPI 발표", "en": "US CPI Release", "date": "2026-02-21", "impact": "High"},
        {"ko": "FOMC 정례 회의", "en": "FOMC Meeting", "date": "2026-02-24", "impact": "Critical"},
        {"ko": "미국 실업수당 청구", "en": "Jobless Claims", "date": "2026-02-26", "impact": "Medium"},
        {"ko": "비농업 고용지수 NFP", "en": "US NFP Report", "date": "2026-03-06", "impact": "High"}
    ]
    res = []
    for ev in raw:
        dt = datetime.strptime(ev['date'], "%Y-%m-%d").date()
        diff = (dt - today).days
        if diff < 0: continue
        dday = "Today" if diff == 0 else f"D-{diff}"
        res.append({"title": ev[lang] if lang in ev else ev['en'], "d_day": dday, "impact": ev['impact'], "date": ev['date']})
    return sorted(res, key=lambda x: x['date'])[:4]

def get_ai_strategy(lang='ko'):
    """종합 전략 리포트 (중복 요청 방지 및 최적화)"""
    # Strategy는 main.py에서 DB 캐싱을 수행하므로 여기서는 중복 AI 호출 방지만 집중
    with _locks["strategy"]:
        fr, oi = fetch_market_info()
        news = fetch_crypto_news(lang='en', translate=False) # 영문 원본 사용 (토큰 절약 및 속도)
        events = get_economic_events(lang=lang)
        
        news_str = "\n".join([f"- {n}" for n in news])
        event_str = "\n".join([f"- {e['title']} ({e['d_day']})" for e in events])

        prompt = f"""
        Act as QuantAI, a Bitcoin Expert Trader. Write a report in {'Korean' if lang=='ko' else 'English'}.
        Data: Funding {fr:.4f}%, OI {oi:,}
        News: {news_str}
        Events: {event_str}
        """

        # OHLCV 데이터 추가
        latest_price = 0.0
        for tf in TIMEFRAMES:
            df = fetch_data(tf)
            if df.empty: continue
            res = analyze_data_advanced(df)
            latest_price = res['close']
            prompt += f"\n[{tf}] Price:{res['close']} RSI:{res['rsi']:.1f} SMC:{res['smc']}"

        prompt += f"""
        \nFormat: 1.Summary(3 lines) 2.Strategy[LONG/SHORT/NEUTRAL] 3.Guide(Entry/TP/SL) 4.Rationale
        End with: SIGNAL_JSON: ```json {{"side": "LONG/SHORT/NONE", "entry": 0.0, "tp": 0.0, "sl": 0.0}} ```
        """

        try:
            res = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
            return {
                "price": latest_price, "strategy": res.text, "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "funding_rate": fr, "open_interest": oi, "news": news, "events": events
            }
        except Exception as e:
            msg = "할당량 초과" if "429" in str(e) else f"Error: {e}"
            return {"price": latest_price, "strategy": msg, "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "funding_rate": fr, "open_interest": oi, "news": [], "events": []}
