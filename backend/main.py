import uvicorn
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from analyzer import get_ai_strategy
from typing import List
import requests

app = FastAPI(
    title="QuantAI API",
    description="BTC/USDT 실시간 AI 분석 백엔드 & 채팅",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- [ 채팅 관리자 (DB 없이 메모리로 관리) ] ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.chat_history: List[dict] = []  # 최근 대화 50개 저장

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # 접속 시 최근 대화 내용 전송
        for msg in self.chat_history:
            await websocket.send_json(msg)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # 대화 저장 (최대 50개)
        self.chat_history.append(message)
        if len(self.chat_history) > 50:
            self.chat_history.pop(0)
            
        # 모두에게 전송
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()


@app.get("/")
def read_root():
    return {"status": "ok", "service": "QuantAI Backend"}


@app.get("/api/health")
async def health():
    """서버 상태 확인"""
    return {"status": "ok"}


# 15분 캐싱을 위한 전역 변수
cache = {
    "data": None,
    "timestamp": None
}
CACHE_DURATION_MINUTES = 15

@app.get("/api/strategy")
async def strategy():
    """
    Gemini AI + 바이낸스 데이터를 기반으로 BTC 매매 전략을 반환합니다.
    (15분 캐싱 적용으로 API 호출 제한 방지)
    """
    global cache
    now = datetime.now()

    # 1. 캐시가 유효하면 (15분 이내) 저장된 데이터 반환
    if cache["data"] and cache["timestamp"]:
        if now - cache["timestamp"] < timedelta(minutes=CACHE_DURATION_MINUTES):
            return cache["data"]

    try:
        # 2. 새로운 데이터 요청
        result = get_ai_strategy()
        
        # 성공 시 캐시 업데이트
        cache["data"] = result
        cache["timestamp"] = now
        
        return result
    except Exception as e:
        # 3. 에러 발생 시 (API 한도 초과 등)
        print(f"Error fetching strategy: {e}")

        # A. 기존 캐시가 있다면 그거라도 반환
        if cache["data"]:
            return cache["data"]
        
        # B. 캐시도 없다면? (서버 재시작 직후 등) -> '분석 대기 중' 가짜 데이터 반환
        # 이렇게 하면 사용자는 절대 에러를 보지 않음
        return {
            "price": 0,
            "strategy": "⚠️ AI 요청량이 많아 잠시 대기 중입니다. (잠시 후 다시 시도됩니다)",
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "funding_rate": 0,
            "open_interest": 0
        }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
