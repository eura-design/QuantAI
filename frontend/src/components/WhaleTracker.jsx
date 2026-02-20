import { useState, useEffect } from 'react'

/**
 * WhaleTracker - 완전 자립형 버전
 * 외부 CSS 및 Config 의존성을 제거하여 렌더링 오류를 원천 차단합니다.
 */
export function WhaleTracker() {
    const [alerts, setAlerts] = useState([])
    const [status, setStatus] = useState('connecting')

    useEffect(() => {
        let eventSource;
        try {
            // 외부 Config 의존성 없이 유연하게 서버 주소 결정
            const baseUrl = window.location.origin.includes('localhost')
                ? 'http://localhost:8000'
                : 'https://quantai-production.up.railway.app';

            eventSource = new EventSource(`${baseUrl}/api/whale/stream`)

            eventSource.onopen = () => setStatus('connected');
            eventSource.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data)
                    if (data && typeof data === 'object') {
                        setAlerts(prev => [data, ...prev].slice(0, 15))
                    }
                } catch (err) {
                    console.error("Whale Parse Error:", err)
                }
            }
            eventSource.onerror = () => {
                setStatus('error');
                eventSource.close();
            }
        } catch (err) {
            console.error("Critical Connection Error:", err)
        }
        return () => { if (eventSource) eventSource.close(); }
    }, [])

    // 스타일 정의 (외부 CSS 의존성 제거)
    const s = {
        container: { flex: 1, display: 'flex', flexDirection: 'column', background: '#0d1117', borderTop: '1px solid #1e2d45', overflow: 'hidden', minHeight: 0 },
        header: { padding: '10px 15px', background: '#131c2e', borderBottom: '1px solid #1e2d45', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
        title: { fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8' },
        badge: { fontSize: '0.6rem', padding: '2px 6px', background: status === 'connected' ? '#26a69a' : '#ef5350', color: 'white', borderRadius: '4px', fontWeight: 800 },
        list: { flex: 1, overflowY: 'auto', padding: '0' },
        empty: { padding: '20px', textAlign: 'center', color: '#475569', fontSize: '0.75rem' },
        item: (side) => ({ display: 'flex', alignItems: 'center', padding: '10px 15px', borderBottom: '1px solid #1e2d45', gap: '12px', background: side === 'BUY' ? 'rgba(38, 166, 154, 0.03)' : 'rgba(239, 83, 80, 0.03)' }),
        system: { padding: '12px 15px', background: 'rgba(30, 45, 69, 0.4)', borderBottom: '1px solid #1e2d45', display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#94a3b8', fontStyle: 'italic', borderLeft: '3px solid #64748b' },
        side: (side) => ({ fontSize: '0.75rem', fontWeight: 800, color: side === 'BUY' ? '#26a69a' : '#ef5350' }),
        amount: { fontSize: '0.9rem', fontWeight: 700, color: '#fff' },
        sub: { display: 'flex', gap: '8px', fontSize: '0.65rem', color: '#475569' },
        time: { fontSize: '0.65rem', color: '#334155' }
    };

    const formatAmount = (amt) => {
        const n = Number(amt) || 0;
        return n >= 1000000 ? (n / 1000000).toFixed(2) + 'M' : (n / 1000).toFixed(0) + 'K';
    }

    try {
        return (
            <div style={s.container}>
                <div style={s.header}>
                    <span style={s.title}>🐋 실시간 고래 추적</span>
                    <span style={s.badge}>{status === 'connected' ? 'LIVE' : 'OFFLINE'}</span>
                </div>
                <div style={s.list}>
                    {alerts.length === 0 ? (
                        <div style={s.empty}>대형 체결 감시 중...</div>
                    ) : (
                        alerts.map((a, i) => {
                            if (a?.type === 'system') return (
                                <div key={i} style={s.system}>
                                    <span>{a.text}</span>
                                    <span style={s.time}>{a.timestamp}</span>
                                </div>
                            );
                            return (
                                <div key={a?.id || i} style={s.item(a?.side)}>
                                    <span style={{ fontSize: '1.2rem' }}>{(Number(a?.amount) >= 1000000 ? '🐋' : Number(a?.amount) >= 500000 ? '🦈' : '🐟')}</span>
                                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <span style={s.side(a?.side)}>{a?.side === 'BUY' ? '매수' : '매도'}</span>
                                            <span style={s.amount}>${formatAmount(a?.amount)}</span>
                                        </div>
                                        <div style={s.sub}>
                                            <span>{Number(a?.qty || 0).toFixed(3)} BTC</span>
                                            <span>@{Number(a?.price || 0).toLocaleString()}</span>
                                        </div>
                                    </div>
                                    <span style={s.time}>{a?.timestamp}</span>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        )
    } catch (renderError) {
        return <div style={s.empty}>⚠️ 컴포넌트 복구 중...</div>
    }
}

// 빌드 시 명칭 불일치를 방지하기 위해 기본 내보내기 추가
export default WhaleTracker;
