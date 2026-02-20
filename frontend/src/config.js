// [환경 설정 파일]
// 모든 API 주소는 이곳에서 통합 관리합니다.
// 로컬 개발 환경과 배포 환경을 자동으로 구분합니다.

const IS_PROD = import.meta.env ? import.meta.env.PROD : true;

const BASE_URL = IS_PROD
    ? 'https://quantai-production.up.railway.app'
    : (typeof window !== 'undefined' && window.location.hostname === 'localhost' ? 'http://localhost:8001' : 'https://quantai-production.up.railway.app');

export const API = {
    BASE_URL,
    STRATEGY: `${BASE_URL}/api/strategy`,
    FEAR_GREED: `${BASE_URL}/api/fear_greed`,
    CHAT_MESSAGES: `${BASE_URL}/api/chat/messages`,
    CHAT_SEND: `${BASE_URL}/api/chat/send`,
    CHAT_STREAM: `${BASE_URL}/api/chat/stream`,
    NEWS: `${BASE_URL}/api/news`,
    DAILY_BRIEF: `${BASE_URL}/api/daily_brief`,
    SENTIMENT: `${BASE_URL}/api/sentiment`,
    VOTE: `${BASE_URL}/api/vote`,
    EVENTS: `${BASE_URL}/api/events`,
    HEALTH: `${BASE_URL}/api/health`
};

export const CONFIG = {
    REFRESH_INTERVAL: 1000 * 60 * 15, // 15분 (차트 갱신 주기)
    RETRY_DELAY: 3000, // 3초 (재요청 대기 시간)
    CHAT_POLLING_INTERVAL: 1000, // (SSE 적용 전 임시 사용)
    SSE_RETRY_INTERVAL: 5000 // SSE 연결 재시도 간격 (5초)
};
