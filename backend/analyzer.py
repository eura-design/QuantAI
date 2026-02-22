import os
import sys
import json
import warnings
import re
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

_exchange_ls = None

def fetch_long_short_ratio():
    """바이낸스 선물 롱/숏 비율 데이터 수집 (requests 직접 호출로 안정성 확보)"""
    import requests
    
    symbol = SYMBOL.replace('/', '')
    periods = ['5m', '15m', '1h']
    
    # 1. Global Long/Short Account Ratio (계정 수 기준)
    # 2. Top Trader Long/Short Account Ratio (상위 트레이더 기준)
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
                    if data_list and len(data_list) > 0:
                        data = data_list[0]
                        l_acc = float(data.get('longAccount', 0))
                        s_acc = float(data.get('shortAccount', 0))
                        
                        if l_acc > 0 or s_acc > 0:
                            # 합계가 1이 아닐 가능성 대비 정규화
                            total = l_acc + s_acc
                            long_p = round((l_acc / total) * 100, 1)
                            short_p = round(100 - long_p, 1)
                            return {"long": long_p, "short": short_p}
            except Exception as e:
                print(f"[ERROR] Fetch LS failed ({url}, {pd}): {e}")
                continue

    # 모든 시도 실패 시에만 fallback
    return {"long": 51.4, "short": 48.6}

def fetch_crypto_news(lang='ko'):
    """실시간 뉴스 수집 (CoinDesk RSS 사용 및 1시간 캐시/번역 적용)"""
    import json
    now = datetime.now()
    cache_file = f"news_cache_{lang}.json"

    # 1. 파일 캐시 확인
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                expiry = datetime.fromisoformat(cache['expiry'])
                if expiry > now:
                    return cache['data']
        except:
            pass

    # 2. 새로운 뉴스 수집
    rss_url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
    try:
        feed = feedparser.parse(rss_url)
        raw_news = [entry.title for entry in feed.entries[:5]]
        
        if not raw_news:
            raise ValueError("No news found")
            
        final_news = raw_news
        # 한국어 요청인 경우 번역 수행
        if lang == 'ko':
            try:
                titles_text = "\n".join(raw_news)
                prompt = f"Translate and summarize these Bitcoin news titles into concise Korean (one line per news):\n{titles_text}"
                res = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
                translated = res.text.strip().split('\n')
                final_news = [t.strip().replace('*', '').replace('-', '').strip() for t in translated if t.strip()][:5]
            except Exception as e:
                print(f"[ERROR] AI News Translation failed: {e}")
                # 세이프가드 제거: 번역 실패 시 빈 목록 반환하여 혼선 방지
                return [] 

        # 캐시 저장
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                "data": final_news,
                "expiry": (now + timedelta(hours=1)).isoformat()
            }, f, ensure_ascii=False)
            
        return final_news
    except Exception as e:
        print(f"[ERROR] News fetch/process failed: {e}")
        return []

# 파일 기반 캐시 (서버 재시작 대응)
BRIEF_CACHE_FILE = "brief_cache.json"

def fetch_ai_daily_brief(lang='ko'):
    """AI 가 생성한 일일 뉴스 요약 (1시간 파일 캐시 적용, 다국어 지원)"""
    import json
    
    now = datetime.now()
    cache_file = f"brief_cache_{lang}.json"
    
    # 1. 파일 캐시 로드 시도
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                expiry = datetime.fromisoformat(cache['expiry'])
                if expiry > now:
                    return cache['data']
        except:
            pass

    # 2. 새로운 브리핑 생성
    news = fetch_crypto_news(lang=lang)
    sentiment = fetch_long_short_ratio()
    events = get_economic_events(lang=lang)
    
    news_text = "\n".join([f"- {n}" for n in news])
    event_text = "\n".join([f"- {e['title']} ({e['d_day']})" for e in events])
    
    prompt_ko = f"""
    당신은 'QuantAI'의 수석 분석가입니다. 다음 **영문 뉴스 데이터** 및 시장 지표를 종합하여 오늘 오전의 **비트코인 핵심 브리핑 3줄**을 작성하세요.
    - **반드시 한국어(Korean)**로 작성할 것
    - 입력 뉴스가 영어이므로, 내용을 파악하여 한국어로 핵심만 요약할 것
    - 마크다운 기호를 쓰지 말 것 (텍스트만 3줄)
    - 줄당 40자 이내로 핵심만 찌를 것
    
    [데이터]
    1. 뉴스(English): {news_text}
    2. 시장심리: 롱 {sentiment['long']}% vs 숏 {sentiment['short']}%
    3. 일정: {event_text}
    """
    
    prompt_en = f"""
    You are the Senior Analyst at 'QuantAI'. Based on the following data, write a **3-line Bitcoin core briefing** for this morning.
    - Write in English.
    - Do not use markdown symbols (3 lines of plain text only).
    - Keep each line under 50 characters, focus on the core.
    
    [Data]
    1. News: {news_text}
    2. Sentiment: Long {sentiment['long']}% vs Short {sentiment['short']}%
    3. Events: {event_text}
    """
    
    prompt = prompt_en if lang == 'en' else prompt_ko

    try:
        response = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
        briefs = response.text.strip().split('\n')
        clean_briefs = [b.replace('*', '').replace('-', '').replace('•', '').strip() for b in briefs if b.strip()]
        result = clean_briefs[:3]
        
        if len(result) >= 1:
            # 파일 캐시 저장
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "data": result,
                    "expiry": (now + timedelta(hours=1)).isoformat()
                }, f, ensure_ascii=False)
            return result
        raise ValueError("Invalid AI Response")
    except Exception as e:
        print(f"[ERROR] AI Daily Briefing failed: {e}")
        # 세이프가드 제거: 실패 시 빈 목록 반환
        return []

def get_economic_events(lang='ko'):
    """주요 거시경제 일정 데이터 (실시간 날짜 기준 D-Day 계산 및 필터링)"""
    now = datetime.now()
    today = now.date()
    
    # 원본 일정 데이터 (일정 추가/수정은 여기에서만 수행)
    raw_events = [
        {"ko": "미국 CPI(소비자물가지수) 발표", "en": "US CPI Release", "date": "2026-02-21", "impact": "High"},
        {"ko": "FOMC 정례 회의", "en": "FOMC Meeting", "date": "2026-02-24", "impact": "Critical"},
        {"ko": "미국 신규 실업수당 청구건수", "en": "US Initial Jobless Claims", "date": "2026-02-26", "impact": "Medium"},
        {"ko": "홍콩 스테이블코인 라이선스 발표", "en": "HK Stablecoin License Announcement", "date": "2026-03-02", "impact": "Medium"},
        {"ko": "미국 비농업 고용지수(NFP) 발표", "en": "US Non-farm Payrolls (NFP)", "date": "2026-03-06", "impact": "High"}
    ]
    
    processed_events = []
    
    for ev in raw_events:
        ev_date = datetime.strptime(ev['date'], "%Y-%m-%d").date()
        diff = (ev_date - today).days
        
        # 날짜별 상태 설정
        if diff < 0:
            # 과거 일정은 표시하지 않음 (또는 필요시 '발표완료' 등으로 표시)
            continue
        elif diff == 0:
            d_day = "Today"
        else:
            d_day = f"D-{diff}"
            
        processed_events.append({
            "title": ev['en'] if lang == 'en' else ev['ko'],
            "d_day": d_day,
            "impact": ev['impact'],
            "date": ev['date']
        })
        
    # 날짜순 정렬 후 상위 3~4개만 반환
    processed_events.sort(key=lambda x: x['date'])
    return processed_events[:4]


def get_ai_strategy(lang='ko') -> dict:
    fr, oi = fetch_market_info()
    news = fetch_crypto_news(lang=lang)
    events = get_economic_events(lang=lang)

    news_str = "\n".join([f"- {n}" for n in news])
    event_str = "\n".join([f"- {e['title']} ({e['d_day']})" for e in events])

    prompt_ko = f"""
    당신은 'QuantAI'라는 비트코인 전문 퀀트 트레이더입니다. 
    다음의 **기술적 분석**과 **실시간 뉴스/이벤트**를 결합하여 **반드시 한국어(Korean)**로 입체적인 리포트를 작성하세요.
    
    [실시간 시장 데이터]
    - 펀딩비: {fr:.4f}% | 미결제약정(OI): {oi:,.0f}
    
    [최신 주요 뉴스]
    {news_str}
    
    [예정된 주요 일정]
    {event_str}
    """

    prompt_en = f"""
    You are a professional Bitcoin quant trader named 'QuantAI'.
    Combine the following **technical analysis** and **real-time news/events** to write a comprehensive report **strictly in English**.
    
    [Real-time Market Data]
    - Funding Rate: {fr:.4f}% | Open Interest (OI): {oi:,.0f}
    
    [Latest Key News]
    {news_str}
    
    [Upcoming Key Events]
    {event_str}
    """
    
    prompt = prompt_en if lang == 'en' else prompt_ko
    
    latest_price = 0.0
    for tf in TIMEFRAMES:
        df = fetch_data(tf)
        if df.empty: continue
        res = analyze_data_advanced(df)
        latest_price = res['close']
        if lang == 'en':
            prompt += f"""
            [{tf} Timeframe Data]
            - Price: {res['close']:.2f} | VWAP: {res['vwap']:.2f}
            - POC: {res['vp']['poc']:.2f} | Sweep: {res['lq_sweep']}
            - ADX: {res['adx']:.2f} | RSI: {res['rsi']:.2f} | SMC: {res['smc']}
            """
        else:
            prompt += f"""
            [{tf} 타임프레임 데이터]
            - 현재가: {res['close']:.2f} | VWAP: {res['vwap']:.2f}
            - POC: {res['vp']['poc']:.2f} | 휩소: {res['lq_sweep']}
            - ADX: {res['adx']:.2f} | RSI: {res['rsi']:.2f} | SMC: {res['smc']}
            """

    if lang == 'en':
        prompt += """
        [Strategy Instructions]
        1. **Fundamental + Technical**: Include the impact of current news (funding rates, regulation) on market sentiment.
        2. **Entry/Exit Strategy**: Suggest entry/stop targets considering volatility around news/events.
        
        [Report Format]
        1. **Market Summary (3-line summary)**: Synthesis of technicals and news.
        2. **Trading Strategy**: [LONG / SHORT / NEUTRAL]
        3. **Guide (Price)**: Entry, Take Profit, Stop Loss.
        4. **Key Rationales**: (1) Technical basis (2) Fundamental/Event basis.
        
        [IMPORTANT]
        At the end of the report, strictly include the following format for tracking (numbers only):
        SIGNAL_JSON:
        ```json
        {"side": "LONG" or "SHORT" or "NONE", "entry": 12345.6, "tp": 12345.6, "sl": 12345.6}
        ```
        """
    else:
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
        response = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
        strategy_text = response.text
        
        # 정규표현식을 사용한 더 안전한 JSON 추출
        json_match = re.search(r'SIGNAL_JSON:\s*```json\s*(\{.*?\})\s*```', strategy_text, re.DOTALL)
        if json_match:
             # 이후 main.py에서 이 마커를 통해 파싱하므로 형식을 유지
             pass
             
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            err_msg = "현재 AI 분석 할당량이 일시적으로 소진되었습니다. 약 1시간 뒤에 다시 시도해주세요." if lang == 'ko' else "AI analysis quota exhausted. Please try again in an hour."
        else:
            err_msg = f"AI 분석 중 오류가 발생했습니다: {e}" if lang == 'ko' else f"AI Analysis Error: {e}"
        strategy_text = err_msg
    
    return {
        "price": latest_price,
        "strategy": strategy_text,
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "funding_rate": fr,
        "open_interest": oi,
        "news": news,
        "events": events
    }
