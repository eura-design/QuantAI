import { useState, useEffect } from 'react'

/**
 * WhaleWatcher - 고래 추적 시스템 (최종 안정화 버전)
 * 컴포넌트 이름을 WhaleTracker에서 WhaleWatcher로 변경하여 빌드 문제를 해결합니다.
 */
export function WhaleWatcher() {
    const [alerts, setAlerts] = useState([]);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        let isAlive = true;
        let es = null;

        try {
            // 접속 주소 결정 로직
            const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            const url = isLocal
                ? 'http://localhost:8000/api/whale/stream'
                : 'https://quantai-production.up.railway.app/api/whale/stream';

            es = new EventSource(url);

            es.onopen = () => { if (isAlive) setIsConnected(true); };
            es.onmessage = (e) => {
                if (!isAlive) return;
                try {
                    const data = JSON.parse(e.data);
                    if (data) {
                        setAlerts(prev => [data, ...prev].slice(0, 10));
                    }
                } catch (err) {
                    console.error("Parse error", err);
                }
            };
            es.onerror = () => {
                if (isAlive) setIsConnected(false);
                if (es) es.close();
            };
        } catch (e) {
            console.error("Connection error", e);
        }

        return () => {
            isAlive = false;
            if (es) es.close();
        };
    }, []);

    const containerStyle = {
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        background: '#0d1117',
        borderTop: '1px solid #1e2d45',
        minHeight: '200px',
        overflow: 'hidden'
    };

    const headerStyle = {
        padding: '10px 15px',
        background: '#131c2e',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid #1e2d45'
    };

    const listStyle = {
        flex: 1,
        overflowY: 'auto',
        padding: '10px'
    };

    const itemStyle = (isBuy) => ({
        padding: '12px',
        marginBottom: '8px',
        background: isBuy ? 'rgba(38, 166, 154, 0.05)' : 'rgba(239, 83, 80, 0.05)',
        borderRadius: '6px',
        border: `1px solid ${isBuy ? 'rgba(38, 166, 154, 0.1)' : 'rgba(239, 83, 80, 0.1)'}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
    });

    return (
        <div style={containerStyle}>
            <div style={headerStyle}>
                <span style={{ color: '#94a3b8', fontSize: '13px', fontWeight: 'bold' }}>🐋 실시간 고래 감시</span>
                <span style={{
                    fontSize: '10px',
                    color: isConnected ? '#26a69a' : '#ef5350',
                    border: `1px solid ${isConnected ? '#26a69a' : '#ef5350'}`,
                    padding: '2px 5px',
                    borderRadius: '3px'
                }}>
                    {isConnected ? 'LIVE' : 'OFFLINE'}
                </span>
            </div>
            <div style={listStyle}>
                {alerts.length === 0 ? (
                    <div style={{ color: '#475569', textAlign: 'center', fontSize: '12px', padding: '40px 0' }}>
                        {isConnected ? '대형 거래를 기다리는 중...' : '서버 연결 시도 중...'}
                    </div>
                ) : (
                    alerts.map((a, i) => {
                        if (a.type === 'system') {
                            return (
                                <div key={i} style={{
                                    padding: '8px 12px',
                                    marginBottom: '10px',
                                    background: 'rgba(30, 45, 69, 0.4)',
                                    borderRadius: '4px',
                                    fontSize: '11px',
                                    color: '#94a3b8',
                                    fontStyle: 'italic',
                                    borderLeft: '3px solid #64748b'
                                }}>
                                    {a.text}
                                </div>
                            );
                        }
                        const isBuy = a.side === 'BUY';
                        const amount = Number(a.amount) || 0;
                        const icon = amount >= 1000000 ? '🐋' : amount >= 500000 ? '🦈' : '🐟';

                        return (
                            <div key={a.id || i} style={itemStyle(isBuy)}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <span style={{ fontSize: '18px' }}>{icon}</span>
                                    <div>
                                        <div style={{ color: isBuy ? '#26a69a' : '#ef5350', fontWeight: 'bold', fontSize: '12px' }}>
                                            {isBuy ? '매수' : '매도'}
                                        </div>
                                        <div style={{ color: '#fff', fontSize: '15px', fontWeight: 'bold' }}>
                                            ${(amount / 1000).toFixed(0)}K
                                        </div>
                                    </div>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <div style={{ color: '#64748b', fontSize: '11px' }}>{a.timestamp}</div>
                                    <div style={{ color: '#475569', fontSize: '10px' }}>{Number(a.qty).toFixed(3)} BTC</div>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
