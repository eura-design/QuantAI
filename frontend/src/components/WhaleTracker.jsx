import React, { useState, useEffect } from 'react'

export function WhaleTracker() {
    const [alerts, setAlerts] = useState([]);
    const [status, setStatus] = useState('Wait');

    useEffect(() => {
        let isMounted = true;
        let es;

        try {
            // 접속 주소 자동 감지
            const url = window.location.hostname === 'localhost'
                ? 'http://localhost:8000/api/whale/stream'
                : 'https://quantai-production.up.railway.app/api/whale/stream';

            es = new EventSource(url);

            es.onopen = () => { if (isMounted) setStatus('Live'); };
            es.onmessage = (e) => {
                if (!isMounted) return;
                try {
                    const data = JSON.parse(e.data);
                    setAlerts(prev => [data, ...prev].slice(0, 10));
                } catch (err) { }
            };
            es.onerror = () => { if (isMounted) setStatus('Retry'); };
        } catch (e) {
            console.error(e);
        }

        return () => {
            isMounted = false;
            if (es) es.close();
        };
    }, []);

    // 인라인 스타일 (상수화)
    const containerStyle = { flex: 1, display: 'flex', flexDirection: 'column', background: '#0d1117', borderTop: '1px solid #1e2d45', minHeight: '200px', overflow: 'hidden' };
    const headerStyle = { padding: '10px', background: '#131c2e', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1e2d45' };
    const listStyle = { flex: 1, overflowY: 'auto', padding: '10px' };
    const systemStyle = { padding: '8px', marginBottom: '8px', background: '#1e2d45', borderRadius: '4px', fontSize: '11px', color: '#94a3b8' };
    const itemStyle = (side) => ({ padding: '10px', marginBottom: '8px', background: side === 'BUY' ? 'rgba(38,166,154,0.1)' : 'rgba(239,83,80,0.1)', borderRadius: '4px', display: 'flex', justifyContent: 'space-between' });

    return (
        <div style={containerStyle}>
            <div style={headerStyle}>
                <span style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 'bold' }}>🐋 고래 추적기</span>
                <span style={{ color: status === 'Live' ? '#26a69a' : '#ef5350', fontSize: '10px' }}>{status}</span>
            </div>
            <div style={listStyle}>
                {alerts.length === 0 ? (
                    <div style={{ color: '#475569', textAlign: 'center', fontSize: '12px' }}>데이터 수신 대기 중...</div>
                ) : (
                    alerts.map((a, i) => (
                        a.type === 'system' ? (
                            <div key={i} style={systemStyle}>{a.text}</div>
                        ) : (
                            <div key={a.id || i} style={itemStyle(a.side)}>
                                <div>
                                    <div style={{ color: a.side === 'BUY' ? '#26a69a' : '#ef5350', fontWeight: 'bold', fontSize: '12px' }}>{a.side === 'BUY' ? '매수' : '매도'}</div>
                                    <div style={{ color: '#fff', fontSize: '14px', fontWeight: 'bold' }}>${(Number(a.amount) / 1000).toFixed(0)}K</div>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <div style={{ color: '#475569', fontSize: '10px' }}>{a.timestamp}</div>
                                    <div style={{ color: '#475569', fontSize: '10px' }}>{Number(a.qty).toFixed(2)} BTC</div>
                                </div>
                            </div>
                        )
                    ))
                )}
            </div>
        </div>
    );
}

export default WhaleTracker;
