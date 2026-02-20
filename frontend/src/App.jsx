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

// 🐋 새로운 이름과 극단적으로 단순한 구조 (에러 방지용)
function BigWhaleMonitor() {
  const [msgs, setMsgs] = useState([]);
  const [status, setStatus] = useState('Wait');

  useEffect(() => {
    let active = true;
    let sse = null;
    try {
      const domain = window.location.hostname === 'localhost'
        ? 'http://localhost:8000'
        : 'https://quantai-production.up.railway.app';

      sse = new EventSource(domain + '/api/whale/stream');
      sse.onopen = () => { if (active) setStatus('ON'); }
      sse.onmessage = (e) => {
        if (!active) return;
        try {
          const d = JSON.parse(e.data);
          if (d) setMsgs(p => [d, ...p].slice(0, 5));
        } catch (err) { }
      }
      sse.onerror = () => { if (active) setStatus('OFF'); }
    } catch (e) { }

    return () => { active = false; if (sse) sse.close(); }
  }, []);

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      background: '#0d1117', borderTop: '1px solid #1e2d45',
      minHeight: '200px', overflow: 'hidden'
    }}>
      <div style={{
        padding: '10px 15px', background: '#131c2e',
        borderBottom: '1px solid #1e2d45', display: 'flex',
        justifyContent: 'space-between', alignItems: 'center'
      }}>
        <span style={{ color: '#94a3b8', fontSize: '13px', fontWeight: 'bold' }}>🐋 실시간 고래 감시</span>
        <span style={{ fontSize: '10px', color: status === 'ON' ? '#26a69a' : '#ef5350' }}>{status}</span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
        {msgs.length === 0 ? (
          <div style={{ color: '#475569', textAlign: 'center', fontSize: '12px', padding: '30px 0' }}>
            거래 데이터 대기 중...
          </div>
        ) : (
          msgs.map((m, i) => (
            <div key={i} style={{
              padding: '10px', marginBottom: '8px',
              background: m.side === 'BUY' ? 'rgba(38,166,154,0.05)' : 'rgba(239,83,80,0.05)',
              borderRadius: '4px', border: '1px solid #1e2d45',
              display: 'flex', justifyContent: 'space-between'
            }}>
              <div>
                <div style={{ color: m.side === 'BUY' ? '#26a69a' : '#ef5350', fontSize: '12px', fontWeight: 'bold' }}>
                  {m.side === 'BUY' ? '매수' : m.side === 'SELL' ? '매도' : '알림'}
                </div>
                <div style={{ color: '#fff', fontSize: '14px', fontWeight: 'bold', marginTop: '2px' }}>
                  ${Number(m.amount || 0) > 0 ? (Number(m.amount) / 1000).toFixed(0) + 'K' : 'SYSTEM'}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ color: '#475569', fontSize: '10px' }}>{m.timestamp}</div>
                {m.qty && <div style={{ color: '#64748b', fontSize: '10px' }}>{Number(m.qty).toFixed(2)} BTC</div>}
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

          {/* 🐋 독립적인 컴포넌트로 에러 방지 */}
          <BigWhaleMonitor />

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
