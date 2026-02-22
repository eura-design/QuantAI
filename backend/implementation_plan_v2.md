# AI 매매 성과 실시간 상태 시각화 구현 계획

AI 매매 성과 섹션의 타이틀 옆에 현재 AI의 실시간 상태(지정가 대기, 포지션 보유 등)를 시각적으로 표시하는 기능을 추가합니다.

## 1. 백엔드 (Backend)
- `backend/core/repository.py`:
    - `TradeRepository.get_current_status()` 메서드 추가: 현재 상태(`OPEN`, `PENDING`, `IDLE`)를 반환하는 로직 구현.
- `backend/main.py`:
    - `/api/trades/stats` 엔드포인트 수정: 응답 데이터에 `current_status` 필드 추가.

## 2. 프론트엔드 (Frontend)
- `frontend/src/translations.js`:
    - `performance.status_labels`: `IDLE`, `PENDING`, `OPEN` 에 대한 한국어/영어 번역 추가.
- `frontend/src/components/TradePerformance.jsx`:
    - 타이틀 오른쪽에 현재 상태를 나타내는 배지(Badge) 컴포넌트 추가.
    - 상태별 색상 적용 (예: IDLE-회색, PENDING-노랑, OPEN-녹색).
- `frontend/src/components/TradePerformance.module.css`:
    - 상태 배지 스타일 및 활성화 상태를 강조하는 펄스(Pulse) 애니메이션 구현.

## 3. 기능 확인
- AI 분석 리포트 생성 시 `PENDING` 상태 변화 확인.
- 가격 도달 시 `OPEN` 상태 변화 확인.
- 매매 종료 후 `IDLE` 상태 복귀 확인.
