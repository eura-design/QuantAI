import uvicorn, sqlite3, requests, asyncio, json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from analyzer import get_ai_strategy, fetch_crypto_news, get_economic_events
from contextlib import contextmanager

DB_NAME = "quant_v2.db"
clients = set()
whale_clients = set()
processed_whale_ids = set() # 중복 전송 방지
rate_limits = {}

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

app = FastAPI(title="QuantAI API", version="1.5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup(): 
    init_db()
    asyncio.create_task(watch_whale_trades())

async def watch_whale_trades():
    """바이낸스에서 대형 체결(고래) 실시간 감시"""
    global processed_whale_ids
    while True:
        try:
            # 최근 100개의 체결 데이터 확인
            res = requests.get("https://api.binance.com/api/v3/trades?symbol=BTCUSDT&limit=100", timeout=5).json()
            new_alerts = []
            for t in res:
                t_id = t['id']
                if t_id in processed_whale_ids: continue
                
                qty = float(t['qty'])
                price = float(t['price'])
                amount = qty * price
                
                # $50,000 이상 체결 시 고래로 포착
                if amount >= 50000:
                    whale_data = {
                        "id": t_id,
                        "price": price,
                        "qty": qty,
                        "amount": amount,
                        "side": "BUY" if not t['isBuyerMaker'] else "SELL",
                        "timestamp": datetime.fromtimestamp(t['time']/1000).strftime('%H:%M:%S'),
                        "is_test": False
                    }
                    new_alerts.append(whale_data)
                processed_whale_ids.add(t_id)
            
            # 너무 오래된 ID는 메모리 관리를 위해 삭제 (최근 1000개 유지)
            if len(processed_whale_ids) > 1000:
                processed_whale_ids = set(list(processed_whale_ids)[-500:])

            # 새 알림이 있으면 모든 클라이언트에게 전송
            for alert in reversed(new_alerts): # 최신순 전송
                for q in list(whale_clients): await q.put(alert)
                
            await asyncio.sleep(2) # 2초마다 갱신
        except Exception as e:
            print(f"Whale Watcher Error: {e}")
            await asyncio.sleep(5)

@app.get("/api/strategy")
def strategy():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM strategy_history ORDER BY id DESC LIMIT 1").fetchone()
        # 15분 캐시 로직
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

@app.get("/api/news")
def get_news():
    return fetch_crypto_news()

@app.get("/api/events")
def get_events():
    return get_economic_events()

@app.get("/api/chat/stream")
async def chat_stream(request: Request):
    async def event_generator():
        q = asyncio.Queue(); clients.add(q)
        try:
            with get_db() as conn:
                # 최근 50개 메시지 로드
                for row in conn.execute("SELECT sender, text, timestamp FROM messages ORDER BY id ASC LIMIT 50").fetchall():
                    yield {"data": json.dumps(dict(row))}
            while True:
                if await request.is_disconnected(): break
                msg = await q.get(); yield {"data": json.dumps(msg)}
        finally: clients.remove(q)
    return EventSourceResponse(event_generator())

@app.get("/api/whale/stream")
async def whale_stream(request: Request):
    async def event_generator():
        q = asyncio.Queue(); whale_clients.add(q)
        try:
            # 접속 시 "연결됨" 확인용 메시지 발송
            yield {"data": json.dumps({
                "id": "system", "price": 0, "qty": 0, "amount": 0, 
                "side": "SYSTEM", "timestamp": datetime.now().strftime('%H:%M:%S'),
                "text": "🐋 고래 추적 시스템이 연결되었습니다."
            })}
            while True:
                if await request.is_disconnected(): break
                whale_alert = await q.get(); yield {"data": json.dumps(whale_alert)}
        finally: whale_clients.remove(q)
    return EventSourceResponse(event_generator())

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

@app.get("/")
def root(): return {"status": "ok", "service": "QuantAI"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
