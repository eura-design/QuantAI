import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from analyzer import get_ai_strategy

app = FastAPI(
    title="QuantAI API",
    description="BTC/USDT 실시간 AI 분석 백엔드",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    """서버 상태 확인"""
    return {"status": "ok"}


@app.get("/api/strategy")
async def strategy():
    """
    Gemini AI + 바이낸스 데이터를 기반으로 BTC 매매 전략을 반환합니다.
    응답 형식:
      price         (float)  : 분석 기준 현재가
      strategy      (str)    : AI 생성 전략 텍스트
      generated_at  (str)    : 생성 시각 (YYYY-MM-DD HH:MM:SS)
      funding_rate  (float)  : 펀딩비(%)
      open_interest (float)  : 미결제약정
    """
    try:
        result = get_ai_strategy()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
