# 구현 계획: 백엔드 로직 통합 및 아키텍처 정문화 (1단계)

본 계획은 백엔드의 중복된 계산 로직을 하나로 통합하고, 유지보수가 용이한 구조로 개선하는 서브시스템 리팩토링입니다. **UI와 API 응답 포맷은 절대 변경하지 않습니다.**

## 1. 개요
현재 `analyzer.py`와 `analyst.py`에 분산된 기술 분석 로직(SMC, CVD, 매물대 등)을 하나의 코어 모듈로 통합하여 "계산의 단일 진실 공급원(Single Source of Truth)"을 만듭니다.

## 2. 주요 작업 내용

### 2.1 코어 모듈 생성
- `backend/core/` 디렉토리 및 `__init__.py` 생성
- `backend/core/indicators.py`: 기술 지표 계산 로직 (VWAP, AVP, SMC, Divergence 등) 통합
- `backend/core/fetcher.py`: 데이터 수집 로직 (Binance OHLCV, OI, Funding Rate) 통합

### 2.2 기존 코드 리팩토링
- `analyzer.py`: 코어 모듈을 참조하도록 수정. 기존 API 응답에 사용되는 함수 시그니처와 리턴 데이터 구조 유지.
- `analyst.py`: 코어 모듈을 참조하도록 수정. 프롬프트 생성 로직만 남기고 계산 로직은 코어 모듈 호출로 변경.

### 2.3 검증 및 안정화
- 리팩토링 후 API(`main.py`)가 기존과 동일한 JSON 데이터를 반환하는지 확인.
- `analyst.py` 실행 시 기존과 동일한 품질의 분석 리포트가 생성되는지 확인.

## 3. 세부 단계 (Step-by-Step)

1. **디렉토리 생성**: `backend/core` 폴더 생성.
2. **함수 추출**: `analyzer.py`와 `analyst.py`에서 공통으로 쓰이는 엔진 로직을 `core/indicators.py`로 이동 및 표준화.
3. **데이터 수집 통합**: `MarketDataFetcher` 로직을 `core/fetcher.py`로 통합.
4. **연결 작업**: `analyzer.py`가 새 코어 모듈을 사용하도록 수정.
5. **검증**: 서버 실행 후 UI 데이터 로딩 확인.

---
**주의사항**: 모든 작업은 백엔드 내부 로직에 한정되며, `main.py`의 엔드포인트 구조나 프론트엔드 코드는 수정하지 않습니다.
