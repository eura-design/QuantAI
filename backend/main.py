import uvicorn, sqlite3, requests, asyncio, json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from analyzer import get_ai_strategy, fetch_crypto_news, get_economic_events, fetch_long_short_ratio, fetch_ai_daily_brief
from contextlib import contextmanager

DB_NAME = "quant_v2.db"
clients = set()
rate_limits = {}

# 투표 데이터 (메모리 저장)
votes = {"bull": 0, "bear": 0, "total": 0}

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try: yield conn
    finally: conn.close()

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, text TEXT, timestamp TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS strategy_history (id INTEGER PRIMARY KEY AUTOINCREMENT, price REAL, strategy TEXT, generated_at TEXT, funding_rate REAL, open_interest REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.commit()

class ChatMessage(BaseModel):
    sender: str; text: str; timestamp: str

class VoteRequest(BaseModel):
    side: str

app = FastAPI(title="QuantAI API", version="1.6.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup(): 
    init_db()

@app.get("/api/strategy")
def strategy():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM strategy_history ORDER BY id DESC LIMIT 1").fetchone()
        if row and datetime.now() - datetime.strptime(row['generated_at'], "%Y-%m-%d %H:%M:%S") < timedelta(minutes=15):
            return dict(row)
    try:
        res = get_ai_strategy()
        if not res['strategy'].startswith("AI 분석 오류"):
            with get_db() as conn:
                conn.execute("INSERT INTO strategy_history (price, strategy, generated_at, funding_rate, open_interest) VALUES (?,?,?,?,?)",
                             (res['price'], res['strategy'], res['generated_at'], res['funding_rate'], res['open_interest']))
                conn.commit()
        return res
    except: return dict(row) if row else {"strategy": "⚠️ 데이터 수집 중..."}

@app.get("/api/fear_greed")
def fear_greed():
    try:
        res = requests.get("https://api.alternative.me/fng/").json()
        return res['data'][0]
    except: return {"value": "50", "value_classification": "Neutral"}

@app.get("/api/sentiment")
def get_sentiment():
    ls = fetch_long_short_ratio()
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
