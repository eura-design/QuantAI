import uvicorn, sqlite3, requests, asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from analyzer import get_ai_strategy
from contextlib import contextmanager

DB_NAME = "quant_v1.db"

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

app = FastAPI(title="QuantAI API", version="1.3.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup(): init_db()

@app.get("/")
def root(): return {"status": "ok", "service": "QuantAI"}

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
        return res if not res['strategy'].startswith("AI 분석 오류") and row else (res if not row else dict(row))
    except: return dict(row) if row else {"price":0, "strategy":"⚠️ 대기 중", "generated_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "funding_rate":0, "open_interest":0}

@app.get("/api/fear_greed")
def fear_greed():
    try: return requests.get("https://api.alternative.me/fng/", timeout=5).json()["data"][0]
    except: return {"value": "50", "value_classification": "Neutral"}

clients = set()

@app.get("/api/chat/messages")
def get_messages():
    with get_db() as conn:
        rows = conn.execute("SELECT sender, text, timestamp FROM messages ORDER BY id DESC LIMIT 50").fetchall()
        return [dict(r) for r in rows][::-1]

@app.get("/api/chat/stream")
async def chat_stream(request: Request):
    async def event_generator():
        q = asyncio.Queue(); clients.add(q)
        try:
            while not await request.is_disconnected():
                try: yield {"data": await asyncio.wait_for(q.get(), 1.0)}
                except asyncio.TimeoutError: yield {"event": "ping", "data": ""}
        finally: clients.remove(q)
    return EventSourceResponse(event_generator())

rate_limits = {}

@app.post("/api/chat/send")
async def send_message(msg: ChatMessage, request: Request):
    ip, now = request.client.host, datetime.now().timestamp()
    limit = rate_limits.setdefault(ip, {"tokens": 5, "last_update": now})
    limit["tokens"] = min(5, limit["tokens"] + int((now - limit["last_update"]) / 10))
    limit["last_update"] = now
    if limit["tokens"] <= 0: raise HTTPException(429, "Too many messages")
    limit["tokens"] -= 1

    with get_db() as conn:
        conn.execute("INSERT INTO messages (sender, text, timestamp) VALUES (?,?,?)", (msg.sender, msg.text, msg.timestamp))
        conn.commit()
    for q in list(clients): await q.put(msg.dict())
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
