import uvicorn
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from analyzer import get_ai_strategy
from typing import List
import requests
import sqlite3
from pydantic import BaseModel

# --- [ DB 설정 ] ---
DB_NAME = "chat.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 채팅 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender TEXT,
                  text TEXT,
                  timestamp TEXT)''')
    # 전략 테이블 (캐싱용)
    c.execute('''CREATE TABLE IF NOT EXISTS strategy_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  price REAL,
                  strategy TEXT,
                  generated_at TEXT,
                  funding_rate REAL,
                  open_interest REAL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

class ChatMessage(BaseModel):
    sender: str
    text: str
    timestamp: str

app = FastAPI(
    title="QuantAI API",
    description="BTC/USDT 실시간 AI 분석 백엔드 & 채팅",
    version="1.3.1"
)

@app.on_event("startup")
def startup_event():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://quant-ai-analyst.vercel.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "QuantAI Backend"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# 15분 캐싱 (DB 기반)
CACHE_DURATION_MINUTES = 15

@app.get("/api/strategy")
async def strategy():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. 최신 데이터 조회
    c.execute("SELECT * FROM strategy_history ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    
    now = datetime.now()
    
    # 2. 캐시 유효성 검사 (15분 이내인지)
    if row:
        last_generated = datetime.strptime(row['generated_at'], "%Y-%m-%d %H:%M:%S")
        if now - last_generated < timedelta(minutes=CACHE_DURATION_MINUTES):
            conn.close()
            return dict(row)

    conn.close()

    try:
        # 3. 새로운 데이터 요청
        result = get_ai_strategy()
        
        # 4. DB에 저장
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO strategy_history 
                     (price, strategy, generated_at, funding_rate, open_interest) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (result['price'], result['strategy'], result['generated_at'], 
                   result['funding_rate'], result['open_interest']))
        conn.commit()
        conn.close()
        
        return result
        
    except Exception as e:
        print(f"Error fetching strategy: {e}")
        # 에러 발생 시 과거 데이터라도 반환
        if row:
            return dict(row)
            
        return {
            "price": 0,
            "strategy": "⚠️ AI 요청량이 많아 잠시 대기 중입니다.",
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "funding_rate": 0,
            "open_interest": 0
        }


# --- [ 공포/탐욕 지수 API ] ---
@app.get("/api/fear_greed")
def get_fear_greed():
    try:
        # 무료 API 호출 (Alternative.me)
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=5)
        data = response.json()
        return data["data"][0] 
    except Exception as e:
        print(f"Fear/Greed Error: {e}")
        return {"value": "50", "value_classification": "Neutral"}

import asyncio
from sse_starlette.sse import EventSourceResponse

# ... (기존 DB 코드 유지)

# SSE 클라이언트 관리 (메모리 큐)
clients = set()

@app.get("/api/chat/messages")
def get_messages():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT sender, text, timestamp FROM messages ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    messages = [dict(row) for row in rows]
    return messages[::-1]

from fastapi import Request

@app.get("/api/chat/stream")
async def message_stream(request: Request):
    async def event_generator():
        q = asyncio.Queue()
        clients.add(q)
        try:
            while True:
                # 연결 끊김 감지
                if await request.is_disconnected():
                    break
                # 큐에서 데이터 기다리기 (무한 대기 아님, 타임오류 방지)
                try:
                    data = await asyncio.wait_for(q.get(), timeout=1.0)
                    yield {"data": data} # SSE 포맷
                except asyncio.TimeoutError:
                    # 1초마다 ping (연결 유지용)
                    yield {"event": "ping", "data": ""}
        except Exception:
            pass
        finally:
            clients.remove(q)

    return EventSourceResponse(event_generator())

# Rate Limit (IP별 도배 방지)
# {ip: {"tokens": 5, "last_update": time}}
rate_limits = {}

from fastapi import Request

@app.post("/api/chat/send")
async def send_message(msg: ChatMessage, request: Request):
    client_ip = request.client.host
    now = datetime.now().timestamp()
    
    # 0. Rate Limit 체크
    if client_ip not in rate_limits:
        rate_limits[client_ip] = {"tokens": 5, "last_update": now}
    
    user_limit = rate_limits[client_ip]
    
    # 토큰 충전 (10초에 1개)
    elapsed = now - user_limit["last_update"]
    new_tokens = int(elapsed / 10)
    if new_tokens > 0:
        user_limit["tokens"] = min(5, user_limit["tokens"] + new_tokens)
        user_limit["last_update"] = now
        
    # 토큰 차감
    if user_limit["tokens"] > 0:
        user_limit["tokens"] -= 1
    else:
        raise HTTPException(status_code=429, detail="Too many messages. Please wait.")

    # 1. DB 저장
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender, text, timestamp) VALUES (?, ?, ?)",
              (msg.sender, msg.text, msg.timestamp))
    conn.commit()
    conn.close()
    
    # 2. 실시간 전파 (모든 클라이언트에게)
    msg_json = msg.json()
    for q in list(clients):
        await q.put(msg_json)
        
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
