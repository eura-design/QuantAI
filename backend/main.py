import asyncio
import json
from datetime import datetime, timedelta

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from analyzer import (
    fetch_ai_daily_brief,
    fetch_crypto_news,
    fetch_long_short_ratio,
    get_ai_strategy,
    get_economic_events,
)
from core.database import init_db
from core.repository import MessageRepository, StrategyRepository, TradeRepository

# 설정 및 캐시 데이터
clients = set()
rate_limits = {}

# 투표 및 캐시 (메모리 저장)
fng_cache = {"data": None, "expiry": None}
ls_cache = {"data": None, "expiry": None}
trade_stats_cache = {"data": None, "needs_update": True}

class ChatMessage(BaseModel):
    sender: str; text: str; timestamp: str

app = FastAPI(title="QuantAI API", version="1.6.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup(): 
    init_db()
    trade_stats_cache["needs_update"] = True  # 캐시 갱신 강제
    asyncio.create_task(monitor_trades())

async def monitor_trades():
    """가상 매매 실시간 감시 및 처리 (1초 주기)"""
    import ccxt
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    symbol = "BTC/USDT"
    
    while True:
        try:
            # 1. 현재가 가져오기
            ticker = exchange.fetch_ticker(symbol)
            curr_price = float(ticker['last'])
            
            # A. 대기 중(PENDING)인 매매 체결 확인
            pending_trades = TradeRepository.get_pending_trades()
            for pt in pending_trades:
                triggered = False
                if pt['side'] == 'LONG' and curr_price <= pt['entry']: triggered = True
                elif pt['side'] == 'SHORT' and curr_price >= pt['entry']: triggered = True
                
                if triggered:
                    TradeRepository.update_trade_status(pt['id'], 'OPEN')
                    print(f"[TRADE] # {pt['id']} Triggered at {curr_price} (Target: {pt['entry']})")

            # B. 진행 중(OPEN)인 매매 승패 확인
            open_trades = TradeRepository.get_open_trades()
            for trade in open_trades:
                status = None
                if trade['side'] == 'LONG':
                    if curr_price >= trade['tp']: status = 'WIN'
                    elif curr_price <= trade['sl']: status = 'LOSS'
                elif trade['side'] == 'SHORT':
                    if curr_price <= trade['tp']: status = 'WIN'
                    elif curr_price >= trade['sl']: status = 'LOSS'
                    
                if status:
                    TradeRepository.update_trade_status(trade['id'], status, curr_price)
                    trade_stats_cache["needs_update"] = True 
                    print(f"[TRADE] Closed #{trade['id']} as {status} at {curr_price}")
                
        except Exception as e:
            print(f"[MONITOR ERROR] {e}")
            
        await asyncio.sleep(1) # 1초마다 정밀 체크

# reset_votes_periodically function removed

@app.get("/api/trades/stats")
async def get_trade_stats():
    """가상 매매 통계 및 최근 기록 조회 (캐시 적용)"""
    if not trade_stats_cache["needs_update"] and trade_stats_cache["data"]:
        return trade_stats_cache["data"]

    wins, losses, win_rate = TradeRepository.get_stats()
    history = TradeRepository.get_history(10)
    current_status = TradeRepository.get_current_status()
    
    data = {
        "wins": wins, 
        "losses": losses, 
        "win_rate": win_rate, 
        "history": history,
        "current_status": current_status
    }
    
    trade_stats_cache["data"] = data
    trade_stats_cache["needs_update"] = False
    return data

@app.get("/api/strategy")
async def strategy(lang: str = "ko"):
    if lang not in ["ko", "en"]: lang = "ko"
    
    prev_row = StrategyRepository.get_latest_strategy(lang)
    if prev_row:
        gen_at = datetime.strptime(prev_row['generated_at'], "%Y-%m-%d %H:%M:%S")
        if datetime.now() - gen_at < timedelta(hours=1):
            return prev_row
            
    try:
        res = get_ai_strategy(lang=lang)
        # 에러 발생 여부와 상관없이 무조건 저장하여 1시간 동안 재시도 방지
        if res:
             # 신호 추출 (정상적인 경우에만)
            if "SIGNAL_JSON:" in res['strategy']:
                try:
                    json_part = res['strategy'].split("SIGNAL_JSON:")[1].strip()
                    json_part = json_part.replace('```json', '').replace('```', '').strip()
                    signal = json.loads(json_part)
                    
                    active = TradeRepository.get_active_trade()
                    if not active and signal['side'] != 'NONE':
                        TradeRepository.upsert_pending_trade(signal['side'], signal['entry'], signal['tp'], signal['sl'])
                    elif signal['side'] == 'NONE':
                        TradeRepository.delete_pending_trades()
                except: pass

            StrategyRepository.add_strategy(
                res['price'], res['strategy'], res['generated_at'], 
                res['funding_rate'], res['open_interest'], lang
            )
        return res
    except Exception as e:
        print(f"[ERROR] Strategy fetch failed: {e}")
        fallback = prev_row if prev_row else {"strategy": "⚠️ 시스템 점검 중..."}
        return fallback

@app.get("/api/fear_greed")
def fear_greed():
    """탐욕/공포 지수 조회 (4시간 캐시 적용)"""
    now = datetime.now()
    if fng_cache["data"] and fng_cache["expiry"] > now:
        return fng_cache["data"]
    
    try:
        res = requests.get("https://api.alternative.me/fng/").json()
        fng_cache["data"] = res['data'][0]
        fng_cache["expiry"] = now + timedelta(hours=4)
        return fng_cache["data"]
    except: 
        if fng_cache["data"]: return fng_cache["data"]
        return {"value": "50", "value_classification": "Neutral"}

@app.get("/api/sentiment")
def get_sentiment():
    """시장 심리 조회 (5분 캐시 적용)"""
    now = datetime.now()
    if ls_cache["data"] and ls_cache["expiry"] > now:
        return {"binance": ls_cache["data"]}
        
    ls = fetch_long_short_ratio()
    ls_cache["data"] = ls
    ls_cache["expiry"] = now + timedelta(minutes=1)
    return {"binance": ls}

# post_vote endpoint removed

@app.get("/api/daily_brief")
def get_brief(lang: str = "ko"):
    if lang not in ["ko", "en"]: lang = "ko"
    return fetch_ai_daily_brief(lang=lang)

@app.get("/api/news")
def get_news(lang: str = "ko"):
    if lang not in ["ko", "en"]: lang = "ko"
    return fetch_crypto_news(lang=lang)

@app.get("/api/events")
def get_events(lang: str = "ko"):
    if lang not in ["ko", "en"]: lang = "ko"
    return get_economic_events(lang=lang)

@app.get("/api/chat/stream")
async def chat_stream(request: Request):
    async def event_generator():
        q = asyncio.Queue(maxsize=20); clients.add(q)
        try:
            messages = MessageRepository.get_recent_messages(50)
            for msg in messages:
                yield {"data": json.dumps(msg)}
            while True:
                if await request.is_disconnected(): break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield {"data": json.dumps(msg)}
                except asyncio.TimeoutError:
                    yield {"comment": "hb"}
        finally: clients.remove(q)
    return EventSourceResponse(event_generator())

@app.post("/api/chat/send")
async def send_message(msg: ChatMessage, request: Request):
    ip, now = request.client.host, datetime.now().timestamp()
    if ip not in rate_limits:
        rate_limits[ip] = {"tokens": 5, "last_update": now}
    limit = rate_limits[ip]
    limit["tokens"] = min(5, limit["tokens"] + int((now - limit["last_update"]) / 10))
    limit["last_update"] = now
    if limit["tokens"] <= 0: raise HTTPException(429, "Too many messages")
    limit["tokens"] -= 1

    MessageRepository.add_message(msg.sender, msg.text, msg.timestamp)
    for q in list(clients):
        try:
            q.put_nowait(msg.dict())
        except asyncio.QueueFull:
            pass
    return {"status": "ok"}

@app.get("/")
def root(): return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
