import { useState, useEffect } from 'react'
import { Header } from './components/Header'
import { ChartPanel } from './components/ChartPanel'
import { ReportPanel } from './components/ReportPanel'
import { FearGreed } from './components/FearGreed'
import { EventCalendar } from './components/EventCalendar'
import { ChatPanel } from './components/ChatPanel'
import { SentimentPanel } from './components/SentimentPanel'
import { DailyBriefing } from './components/DailyBriefing'
import { TradePerformance } from './components/TradePerformance'
import ErrorBoundary from './components/ErrorBoundary'
import { useStrategy } from './hooks/useStrategy'
import './App.css'

// 🐋 실시간 고래 감시 컴포넌트
function BigWhaleMonitor() {
  const [msgs, setMsgs] = useState([]);
  const [status, setStatus] = useState('Wait');

  useEffect(() => {
    let active = true;
    let ws = null;
    const connect = () => {
      try {
        ws = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@trade');
        ws.onopen = () => { if (active) setStatus('ON'); }
        ws.onmessage = (e) => {
          if (!active) return;
          try {
            const m = JSON.parse(e.data);
            const amount = parseFloat(m.p) * parseFloat(m.q);
            if (amount >= 50000) {
              const alert = {
                side: m.m ? "SELL" : "BUY",
                amount: amount,
                timestamp: new Date(m.T).toTimeString().slice(0, 8)
              };
              setMsgs(p => [alert, ...p].slice(0, 15));
            }
          } catch (err) { }
        }
        ws.onerror = () => { if (active) setStatus('OFF'); }
        ws.onclose = () => { if (active) setTimeout(connect, 5000); }
      } catch (e) { }
    };
    connect();
    return () => { active = false; if (ws) ws.close(); }
  }, []);

  return (
    <div className="glass-card" style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: '16px 20px' }}>
      <div style={{
        fontFamily: 'Outfit', fontSize: '0.95rem', fontWeight: '800', color: 'var(--text-primary)',
        marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '10px'
      }}>
        <span>🐋 실시간 고래 감시</span>
        <span style={{
          fontSize: '0.6rem',
          fontWeight: '900',
          color: status === 'ON' ? 'var(--bull)' : 'var(--bear)',
          marginLeft: 'auto',
          background: 'rgba(255,255,255,0.05)',
          padding: '1px 6px',
          borderRadius: '4px',
          border: '1px solid currentColor'
        }}>● {status}</span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
        {msgs.length === 0 ? <div style={{ color: 'var(--text-muted)', textAlign: 'center', fontSize: '0.75rem', marginTop: '20px' }}>데이터 대기 중...</div> :
          msgs.map((m, i) => (
            <div key={i} style={{
              display: 'flex',
              justify- content: 'space-between',
        padding: '8px 0',
        borderBottom: '1px solid var(--border-main)'
            }}>
        <span style={{ color: m.side === 'BUY' ? 'var(--bull)' : 'var(--bear)', fontSize: '0.8rem', fontWeight: '800' }}>
          {m.side} {(m.amount / 1000).toFixed(0)}K
        </span>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem', fontWeight: '500' }}>{m.timestamp}</span>
      </div>
      ))
        }
    </div>
    </div >
  );
}

function App() {
  const { data, loading, error, refetch } = useStrategy()

  return (
    <div className="app">
      <Header />
      <div className="main-layout">

        {/* 1열: 차트 + 하단 지표 4종 */}
        <div style={{ gridColumn: '1', gridRow: '1 / 3', display: 'flex', flexDirection: 'column', gap: '16px', minHeight: 0 }}>
          <div style={{ flex: 2.2, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <ErrorBoundary>
              <ChartPanel />
            </ErrorBoundary>
          </div>
          <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: '16px', minHeight: 0 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ flex: 0.9, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
                <ErrorBoundary>
                  <SentimentPanel />
                </ErrorBoundary>
              </div>
              <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
                <ErrorBoundary>
                  <FearGreed />
                </ErrorBoundary>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
              <ErrorBoundary>
                <BigWhaleMonitor />
              </ErrorBoundary>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
              <ErrorBoundary>
                <EventCalendar />
              </ErrorBoundary>
            </div>
          </div>
        </div>

        {/* 2열: 성과 + 리포트 */}
        <div className="area-sidebar-1" style={{ display: 'flex', flexDirection: 'column', gap: '16px', minHeight: 0 }}>
          <div style={{ height: '180px', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <ErrorBoundary>
              <TradePerformance />
            </ErrorBoundary>
          </div>
          <div className="flex-grow" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <ErrorBoundary>
              <ReportPanel data={data} loading={loading} error={error} onRefresh={refetch} />
            </ErrorBoundary>
          </div>
        </div>

        {/* 3열: 요약 + 채팅 */}
        <div className="area-sidebar-2" style={{ display: 'flex', flexDirection: 'column', gap: '16px', minHeight: 0 }}>
          <div style={{ height: '180px', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <ErrorBoundary>
              <DailyBriefing />
            </ErrorBoundary>
          </div>
          <div className="flex-grow" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <ErrorBoundary>
              <ChatPanel />
            </ErrorBoundary>
          </div>
        </div>

      </div>
    </div>
  )
}

export default App
