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
    <div style={{
      height: '100%', display: 'flex', flexDirection: 'column',
      background: '#0d1117', border: '1px solid #1e2d45', borderRadius: '12px', overflow: 'hidden'
    }}>
      <div style={{ padding: '8px 12px', background: '#131c2e', borderBottom: '1px solid #1e2d45', fontSize: '11px', color: '#94a3b8', fontWeight: 'bold', display: 'flex', justifyContent: 'space-between' }}>
        <span>🐋 실시간 고래 감시</span>
        <span style={{ color: status === 'ON' ? '#26a69a' : '#ef5350' }}>● {status}</span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
        {msgs.length === 0 ? <div style={{ color: '#475569', textAlign: 'center', fontSize: '11px', marginTop: '20px' }}>데이터 대기 중...</div> :
          msgs.map((m, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
              <span style={{ color: m.side === 'BUY' ? '#26a69a' : '#ef5350', fontSize: '12px', fontWeight: 'bold' }}>{m.side} ${(m.amount / 1000).toFixed(0)}K</span>
              <span style={{ color: '#445566', fontSize: '10px' }}>{m.timestamp}</span>
            </div>
          ))
        }
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

        {/* 1열: 차트 + 하단 지표 4종 */}
        <div style={{ gridColumn: '1', gridRow: '1 / 3', display: 'flex', flexDirection: 'column', gap: '12px', minHeight: 0 }}>
          <div style={{ flex: 2.2, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <ErrorBoundary>
              <ChartPanel />
            </ErrorBoundary>
          </div>
          <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: '12px', minHeight: 0 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ flex: 1.5, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
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
        <div className="area-sidebar-1" style={{ display: 'flex', flexDirection: 'column', gap: '12px', minHeight: 0 }}>
          <div style={{ display: 'flex', flexDirection: 'column', border: '1px solid #1e2d45', borderRadius: '12px', background: '#0d1117', overflow: 'hidden' }}>
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
        <div className="area-sidebar-2" style={{ display: 'flex', flexDirection: 'column', gap: '12px', minHeight: 0 }}>
          <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
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
