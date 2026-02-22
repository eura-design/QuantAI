# Implementation Plan - QuantAI "Oasis" Theme Update

## 목적
- 퀀트 시스템의 정밀함(데이터)과 쉼터의 안락함(감성)을 조화시킨 "Oasis" 테마 적용.
- 사용자의 매매 피로도를 낮추고 심리적 안정감을 주는 UI/UX 개선.

## 주요 변경 사항

### 1. 디자인 시스템 (Visual)
- **색상 팔레트:** 지루한 블랙 대신 깊이 있는 네이비(`--bg-deep: #0f172a`)와 차분한 에메랄드(`--accent-emerald: #10b981`) 테마 적용.
- **글래스모피즘 강화:** `App.css`의 변수들을 수정하여 더 부드러운 블러 효과와 투명도 조절.

### 2. 오늘의 안식처 브리핑 (Decision Summary)
- `OasisSummary.jsx` 컴포넌트 신규 생성.
- 메인 레이아웃 상단에 배치하여 사용자가 접속하자마자 현재 시장 대응 방안을 한 문장으로 인지하게 함.

### 3. 언어 및 페르소나 (Copywriting)
- **Header:** "QuantAI" 로고 옆에 "Your Trading Oasis" 부문구 추가.
- **SentimentPanel:** "시장 심리 리포트" -> "시장 참여자들의 정서적 발걸음".
- **DailyBriefing:** "AI 데일리 3줄 요약" -> "내일의 휴식을 위한 오늘의 체크포인트".

## 상세 작업 단계

### Phase 1: 디자인 시스템 업데이트
- [ ] `frontend/src/App.css` 수정: 네이비/에메랄드 기반 변수 업데이트.
- [ ] `frontend/src/index.css` 수정: 배경색 일관성 유지.

### Phase 2: 요약 컴포넌트 추가
- [ ] `frontend/src/components/OasisSummary.jsx` 생성.
- [ ] `frontend/src/components/OasisSummary.module.css` 생성.
- [ ] `frontend/src/App.jsx` 수정: 레이아웃 상단에 `OasisSummary` 배치.

### Phase 3: 기존 컴포넌트 텍스트 및 스타일 튜닝
- [ ] `frontend/src/components/Header.jsx`: 로고 및 상태 문구 수정.
- [ ] `frontend/src/components/SentimentPanel.jsx`: 제목 및 게이지 스타일 조정.
- [ ] `frontend/src/components/DailyBriefing.jsx`: 타이틀 수정.

### Phase 4: 검증
- [ ] 로컬 환경에서 프론트/백엔드 실행.
- [ ] 테마 적용 확인 및 가시성 테스트.
