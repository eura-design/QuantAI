import { useState, useEffect } from 'react'
import { Header } from './components/Header'
import { ChartPanel } from './components/ChartPanel'
import { ReportPanel } from './components/ReportPanel'
import { FearGreed } from './components/FearGreed'
import { EventCalendar } from './components/EventCalendar'
import { ChatPanel } from './components/ChatPanel'
import ErrorBoundary from './components/ErrorBoundary'
import { useStrategy } from './hooks/useStrategy'
import './App.css'

/**
 * WhaleWatcher - App.jsx 내부 삽입 버전 (에러 원천 차단)
 */
function WhaleWatcher() {
  const [alerts, setAlerts] = useState([]);
  const [status, setStatus] = useState('Wait');

  useEffect(() => {
    let isAlive = true;
    let es = null;
    try {
      const url = window.location.hostname === 'localhost'
        ? 'http://localhost:8000/api/whale/stream'
        : 'https://quantai-production.up.railway.app/api/whale/stream';
      es = new EventSource(url);
      es.onopen = () => { if (isAlive) setStatus('Live'); };
      es.onmessage = (e) => {
        if (!isAlive) return;
        try {
          const data = JSON.parse(e.data);
          if (data) setAlerts(prev => [data, ...prev].slice(0, 5));
        } catch (err) { }
      };
      es.onerror = () => { if (isAlive) setStatus('Retry'); };
    } catch (e) { }
    return () => { isAlive = false; if (es) es.close(); };
  }, []);

  const s = {
    container: { flex: 1, display: 'flex', flexDirection: 'column', background: '#0d1117', borderTop: '1px solid #1e2d45', minHeight: '180px', overflow: 'hidden' },
    header: { padding: '10px 15px', background: '#131c2e', borderBottom: '1px solid #1e2d45', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
    item: (isBuy) => ({ padding: '10px', marginBottom: '6px', background: isBuy ? 'rgba(38,166,154,0.05)' : 'rgba(239,83,80,0.05)', borderRadius: '4px', display: 'flex', justifyContent: 'space-between', fontSize: '12px' })
  };

  return (
    <div style={s.container}>
      <div style={s.header}>
        <span style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 'bold' }}>🐋 실시간 고래 감시</span>
        <span style={{ color: status === 'Live' ? '#26a69a' : '#ef5350', fontSize: '10px' }}>{status}</span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
        {alerts.length === 0 ? (
          <div style={{ color: '#475569', textAlign: 'center', fontSize: '11px', padding: '20px 0' }}>데이터 대기 중...</div>
        ) : (
          alerts.map((a, i) => (
            <div key={i} style={s.item(a.side === 'BUY')}>
              <div>
                <div style={{ color: a.side === 'BUY' ? '#26a69a' : '#ef5350', fontWeight: 'bold' }}>{a.side === 'BUY' ? '매수' : '매도'}</div>
                <div style={{ color: '#fff', fontWeight: 'bold' }}>${(Number(a.amount || 0) / 1000).toFixed(0)}K</div>
              </div>
              <div style={{ textAlign: 'right', color: '#475569', fontSize: '10px' }}>
                <div>{a.timestamp}</div>
                <div>{Number(a.qty || 0).toFixed(2)} BTC</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function App() {
  const { data, loading, error, refetch } = useStrategy()

  return (
    <div className="app">
      <Header />
      <div className="main-layout">
        <ErrorBoundary>
          <ChartPanel />
        </ErrorBoundary>

        <div className="sidebar-column">
          <ErrorBoundary>
            <ReportPanel data={data} loading={loading} error={error} onRefresh={refetch} />
          </ErrorBoundary>

          <ErrorBoundary>
            <WhaleWatcher />
          </ErrorBoundary>

          <ErrorBoundary>
            <FearGreed />
          </ErrorBoundary>
        </div>

        <div className="sidebar-column">
          <ErrorBoundary>
            <EventCalendar />
          </ErrorBoundary>
          <ErrorBoundary>
            <ChatPanel />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  )
}

export default App
