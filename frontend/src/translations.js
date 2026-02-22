export const translations = {
    ko: {
        common: {
            loading: '데이터 로드 중...',
            error: '에러가 발생했습니다.',
            live: 'LIVE',
            connecting: '연결 중...',
        },
        header: {
            subtitle: 'Your Trading Oasis',
            connecting: '연결 중...',
            candleSuffix: '봉',
        },
        chart: {
            live: 'LIVE · BTC/USDT 연결됨',
            connecting: '연결 끊김 · 재연결 중...',
            fail: '데이터 로드 실패',
            t1m: '1분', t5m: '5분', t15m: '15분', t1h: '1시간', t4h: '4시간', t1d: '1일',
            updateTime: '마지막 업데이트',
        },
        sentiment: {
            title: '현재 롱 / 숏 비율',
            subtitle: '바이낸스 선물 포지션 심리',
            binance: 'Binance Futures',
        },
        fearGreed: {
            title: '공포 & 탐욕 지수',
            ExtremeFear: '극도 공포',
            Fear: '공포',
            Neutral: '중립',
            Greed: '탐욕',
            ExtremeGreed: '극도 탐욕',
            now: '지금',
        },
        events: {
            title: '📅 주요 경제 일정',
        },
        briefing: {
            title: '✨ AI 뉴스 요약',
            loading: 'AI 브리핑 생성 중...',
            placeholders: [
                '뉴스 요약을 불러올 수 있습니다.',
                '현재 시장 변동성에 유의하세요.',
                '주요 경제 일정을 확인하세요.'
            ]
        },
        whale: {
            title: '🐋 고래 실시간 거래',
            status: 'Monitoring',
        },
        performance: {
            title: 'AI 매매 성과',
            winRate: '평균 승률',
            wins: '수익 거래',
            losses: '손실 거래',
            winUnit: '승',
            lossUnit: '패',
            loading: '성과 집계 중...',
            history: '최근 매매 기록',
            side: {
                LONG: '롱',
                SHORT: '숏'
            },
            status: {
                win: '수익',
                loss: '손실',
                open: '진행중'
            },
            status_labels: {
                IDLE: '시장 관망중',
                PENDING: '지정가 대기중',
                OPEN: '포지션 보유중'
            }
        },
        chat: {
            title: '🔥 실시간 토론방',
            placeholder: '매매 의견을 나눠보세요...',
            send: '전송',
            error: '메시지 전송 실패. 네트워크를 확인하세요.',
            traderPrefix: '개미',
            online: '온라인',
        },
        report: {
            title: 'AI 실시간 전략 리포트',
            refresh: '새로고침',
            loading: 'AI 분석 리포트 생성 중...',
            generatedAt: '보고서 생성 시각',
            metrics: {
                volatility: '시장 변동성',
                strength: '추세 강도',
                sentiment: '투자 심리'
            }
        },
        oasis: {
            title: 'OASIS',
            loading: 'AI 분석 대기 중...',
            bias: '현재 시장 편향성',
            target: '단기 목표가',
            stop: '방어 손절가',
            msgNone: 'AI가 신중하게 시장 진입 기회를 탐색 중입니다.',
            msgLong: '강한 매수세가 감지되었습니다. 눌림목 매수 전략이 유효해 보입니다.',
            msgShort: '매도 압력이 거세지고 있습니다. 반등 시 매도 포지션이 유리합니다.',
        }
    },
    en: {
        common: {
            loading: 'Loading data...',
            error: 'An error occurred.',
            live: 'LIVE',
            connecting: 'Connecting...',
        },
        header: {
            subtitle: 'Your Trading Oasis',
            connecting: 'Connecting...',
            candleSuffix: ' Candle',
        },
        chart: {
            live: 'LIVE · BTC/USDT Connected',
            connecting: 'Disconnected · Reconnecting...',
            fail: 'Failed to load data',
            t1m: '1m', t5m: '5m', t15m: '15m', t1h: '1h', t4h: '4h', t1d: '1d',
            updateTime: 'Last update',
        },
        sentiment: {
            title: 'Long / Short Ratio',
            subtitle: 'Binance Futures Sentiment',
            binance: 'Binance Futures',
        },
        fearGreed: {
            title: 'CRYPTO FEAR & GREED',
            ExtremeFear: 'Extreme Fear',
            Fear: 'Fear',
            Neutral: 'Neutral',
            Greed: 'Greed',
            ExtremeGreed: 'Extreme Greed',
            now: 'NOW',
        },
        events: {
            title: '📅 Economic Calendar',
        },
        briefing: {
            title: '✨ AI News Summary',
            loading: 'Generating AI Briefing...',
            placeholders: [
                'Could not load news summary.',
                'Please be mindful of current market volatility.',
                'Please check the major economic calendar.'
            ]
        },
        whale: {
            title: '🐋 Whale Tracker',
            status: 'Monitoring',
        },
        performance: {
            title: 'AI Performance',
            winRate: 'Win Rate',
            wins: 'Wins',
            losses: 'Losses',
            winUnit: 'W',
            lossUnit: 'L',
            loading: 'Calculating...',
            history: 'Recent Trades',
            side: {
                LONG: 'LONG',
                SHORT: 'SHORT'
            },
            status: {
                win: 'WIN',
                loss: 'LOSS',
                open: 'OPEN'
            },
            status_labels: {
                IDLE: 'Watching',
                PENDING: 'Pending Order',
                OPEN: 'In Position'
            }
        },
        chat: {
            title: '🔥 Live Discussion',
            placeholder: 'Share your ideas...',
            send: 'Send',
            error: 'Network Error.',
            traderPrefix: 'Trader',
            online: 'ONLINE',
        },
        report: {
            title: 'AI Real-time Strategy Report',
            refresh: 'Refresh',
            loading: 'Generating AI Report...',
            generatedAt: 'Report Generated',
            metrics: {
                volatility: 'Volatility',
                strength: 'Trend Strength',
                sentiment: 'Sentiment'
            }
        },
        oasis: {
            title: 'OASIS',
            loading: 'Waiting for AI Analysis...',
            bias: 'Market Bias',
            target: 'Target Price',
            stop: 'Stop Loss',
            msgNone: 'AI is cautiously scouting for market entry opportunities.',
            msgLong: 'Strong buying pressure detected. Dip-buying strategies favored.',
            msgShort: 'Selling pressure is rising. Shorting on rallies is favorable.',
        }
    }
};
