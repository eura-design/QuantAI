import asyncio
import json
import sqlite3
from contextlib import contextmanager
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

# 설정 및 캐시 데이터
DB_NAME = "quant_v2.db"
DB_TIMEOUT = 10.0
clients = set()
rate_limits = {}

# 투표 및 캐시 (메모리 저장)
votes = {"bull": 0, "bear": 0, "total": 0}
fng_cache = {"data": None, "expiry": None}
ls_cache = {"data": None, "expiry": None}
trade_stats_cache = {"data": None, "needs_update": True}

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=DB_TIMEOUT)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, text TEXT, timestamp TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS strategy_history (id INTEGER PRIMARY KEY AUTOINCREMENT, price REAL, strategy TEXT, generated_at TEXT, funding_rate REAL, open_interest REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        # 가상 매매 테이블
        c.execute('''CREATE TABLE IF NOT EXISTS virtual_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            side TEXT,
            entry REAL,
            tp REAL,
            sl REAL,
            status TEXT DEFAULT 'OPEN',
            close_price REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()

class ChatMessage(BaseModel):
    sender: str; text: str; timestamp: str

class VoteRequest(BaseModel):
    side: str

app = FastAPI(title="QuantAI API", version="1.6.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup(): 
    init_db()
    asyncio.create_task(reset_votes_periodically())
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
            
            with get_db() as conn:
                c = conn.cursor()
                
                # A. 대기 중(PENDING)인 매매 체결 확인
                c.execute("SELECT id, side, entry FROM virtual_trades WHERE status='PENDING'")
                pending_trades = c.fetchall()
                for pt in pending_trades:
                    t_id, side, entry = pt['id'], pt['side'], pt['entry']
                    triggered = False
                    if side == 'LONG' and curr_price <= entry: triggered = True
                    elif side == 'SHORT' and curr_price >= entry: triggered = True
                    
                    if triggered:
                        conn.execute("UPDATE virtual_trades SET status='OPEN' WHERE id=?", (t_id,))
                        print(f"[TRADE] # {t_id} Triggered at {curr_price} (Target: {entry})")

                # B. 진행 중(OPEN)인 매매 승패 확인
                c.execute("SELECT id, side, tp, sl FROM virtual_trades WHERE status='OPEN'")
                open_trades = c.fetchall()
                for trade in open_trades:
                    t_id, side, tp, sl = trade['id'], trade['side'], trade['tp'], trade['sl']
                    status = None
                    if side == 'LONG':
                        if curr_price >= tp: status = 'WIN'
                        elif curr_price <= sl: status = 'LOSS'
                    elif side == 'SHORT':
                        if curr_price <= tp: status = 'WIN'
                        elif curr_price >= sl: status = 'LOSS'
                        
                    if status:
                        conn.execute("UPDATE virtual_trades SET status=?, close_price=? WHERE id=?", (status, curr_price, t_id))
                        trade_stats_cache["needs_update"] = True 
                        print(f"[TRADE] Closed #{t_id} as {status} at {curr_price}")
                
                conn.commit()
                
        except Exception as e:
            print(f"[MONITOR ERROR] {e}")
            
        await asyncio.sleep(1) # 1초마다 정밀 체크

async def reset_votes_periodically():
    """4시간마다 투표 초기화 (00, 04, 08, 12, 16, 20시)"""
    global votes
    last_period = datetime.now().hour // 4
    while True:
        await asyncio.sleep(60) # 1분마다 체크
        curr_period = datetime.now().hour // 4
        if curr_period != last_period:
            votes = {"bull": 0, "bear": 0, "total": 0}
            last_period = curr_period
            print(f"[{datetime.now()}] 투표 데이터가 새 세션을 위해 초기화되었습니다.")

@app.get("/api/trades/stats")
async def get_trade_stats():
    """가상 매매 통계 및 최근 기록 조회 (캐시 적용)"""
    if not trade_stats_cache["needs_update"] and trade_stats_cache["data"]:
        return trade_stats_cache["data"]

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM virtual_trades WHERE status='WIN'")
        wins = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM virtual_trades WHERE status='LOSS'")
        losses = c.fetchone()[0]
        c.execute("SELECT * FROM virtual_trades ORDER BY id DESC LIMIT 10")
        history = [dict(row) for row in c.fetchall()]
        
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        data = {"wins": wins, "losses": losses, "win_rate": round(win_rate, 1), "history": history}
        
        trade_stats_cache["data"] = data
        trade_stats_cache["needs_update"] = False
        return data

@app.get("/api/strategy")
async def strategy():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM strategy_history ORDER BY id DESC LIMIT 1").fetchone()
        if row and datetime.now() - datetime.strptime(row['generated_at'], "%Y-%m-%d %H:%M:%S") < timedelta(minutes=15):
            return dict(row)
    try:
        res = get_ai_strategy()
        if not res['strategy'].startswith("AI 분석 오류"):
            # 가상 매매 신호 추출 및 저장
            try:
                if "SIGNAL_JSON:" in res['strategy']:
                    json_part = res['strategy'].split("SIGNAL_JSON:")[1].strip()
                    # 마크다운 백틱 제거
                    json_part = json_part.replace('```json', '').replace('```', '').strip()
                    signal = json.loads(json_part)
                    
                    with get_db() as conn:
                        # 1. 현재 진행 중인(OPEN) 포지션이 있는지 확인
                        active = conn.execute("SELECT id FROM virtual_trades WHERE status='OPEN'").fetchone()
                        
                        if active:
                            print(f"[TRADE] Active position exists. New signal ignored.")
                        elif signal['side'] != 'NONE':
                            # 2. 대기 중(PENDING)인 매매가 있으면 최신 정보로 갱신, 없으면 신규 생성
                            pending = conn.execute("SELECT id FROM virtual_trades WHERE status='PENDING'").fetchone()
                            if pending:
                                conn.execute(
                                    "UPDATE virtual_trades SET side=?, entry=?, tp=?, sl=? WHERE id=?",
                                    (signal['side'], signal['entry'], signal['tp'], signal['sl'], pending['id'])
                                )
                                print(f"[TRADE] Pending signal updated to latest: {signal['side']} at {signal['entry']}")
                            else:
                                conn.execute(
                                    "INSERT INTO virtual_trades (side, entry, tp, sl, status) VALUES (?, ?, ?, ?, 'PENDING')",
                                    (signal['side'], signal['entry'], signal['tp'], signal['sl'])
                                )
                                print(f"[TRADE] New PENDING signal: {signal['side']} at {signal['entry']}")
                            conn.commit()
                            trade_stats_cache["needs_update"] = True 
                        else:
                            # 신호가 NONE이고 기존 PENDING이 있으면 삭제 (관망으로 변경)
                            conn.execute("DELETE FROM virtual_trades WHERE status='PENDING'")
                            conn.commit()
                            print(f"[TRADE] Signal is NONE. Any pending orders removed.")
            except Exception as e:
                print(f"[ERROR] Signal extraction failed: {e}")

            with get_db() as conn:
                conn.execute("INSERT INTO strategy_history (price, strategy, generated_at, funding_rate, open_interest) VALUES (?,?,?,?,?)",
                             (res['price'], res['strategy'], res['generated_at'], res['funding_rate'], res['open_interest']))
                conn.commit()
        return res
    except Exception as e:
        print(f"[ERROR] Strategy fetch failed: {e}")
        return dict(row) if row else {"strategy": "⚠️ 데이터 수집 중..."}

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
        return {"binance": ls_cache["data"], "votes": votes}
        
    ls = fetch_long_short_ratio()
    ls_cache["data"] = ls
    ls_cache["expiry"] = now + timedelta(minutes=5)
    return {"binance": ls, "votes": votes}

@app.post("/api/vote")
def post_vote(req: VoteRequest):
    if req.side == "bull": votes["bull"] += 1
    else: votes["bear"] += 1
    votes["total"] += 1
    return votes

@app.get("/api/daily_brief")
def get_brief():
    return fetch_ai_daily_brief()

@app.get("/api/news")
def get_news():
    return fetch_crypto_news()

@app.get("/api/events")
def get_events():
    return get_economic_events()

@app.get("/api/chat/stream")
async def chat_stream(request: Request):
    async def event_generator():
        q = asyncio.Queue(maxsize=20); clients.add(q)
        try:
            with get_db() as conn:
                for row in conn.execute("SELECT sender, text, timestamp FROM messages ORDER BY id ASC LIMIT 50").fetchall():
                    yield {"data": json.dumps(dict(row))}
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

    with get_db() as conn:
        conn.execute("INSERT INTO messages (sender, text, timestamp) VALUES (?,?,?)", (msg.sender, msg.text, msg.timestamp))
        conn.commit()
    for q in list(clients):
        try:
            q.put_nowait(msg.dict())
        except asyncio.QueueFull:
            pass
    return {"status": "ok"}

@app.get("/")
def root(): return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
