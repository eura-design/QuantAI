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
    const BINANCE_TRADE_WS = 'wss://stream.binance.com:9443/ws/btcusdt@trade';

    const connect = () => {
      try {
        ws = new WebSocket(BINANCE_TRADE_WS);
        ws.onopen = () => { if (active) setStatus('ON'); }
        ws.onmessage = (e) => {
          if (!active) return;
          try {
            const m = JSON.parse(e.data);
            const amount = parseFloat(m.p) * parseFloat(m.q);
            if (amount >= 50000) {
              const alert = {
                tier: amount >= 100000 ? "WHALE" : "DOLPHIN",
                side: m.m ? "SELL" : "BUY",
                amount: amount,
                timestamp: new Date(m.T).toTimeString().slice(0, 8)
              };
              setMsgs(p => [alert, ...p].slice(0, 20));
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
      background: '#0d1117', border: '1px solid #1e2d45', borderRadius: '12px',
      overflow: 'hidden'
    }}>
      <div style={{ padding: '8px 12px', background: '#131c2e', borderBottom: '1px solid #1e2d45', fontSize: '11px', color: '#94a3b8', fontWeight: 'bold' }}>🐋 실시간 고래 감시</div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
        {msgs.length === 0 ? <div style={{ color: '#475569', textAlign: 'center', fontSize: '10px', padding: '10px' }}>데이터 대기 중...</div> :
          msgs.map((m, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
              <span style={{ color: m.side === 'BUY' ? '#26a69a' : '#ef5350', fontSize: '11px', fontWeight: 'bold' }}>{m.side === 'BUY' ? '▲' : '▼'} ${(m.amount / 1000).toFixed(0)}K</span>
              <span style={{ color: '#475569', fontSize: '9px' }}>{m.timestamp}</span>
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

        {/* 1. 좌측: 차트 및 하단 지표 */}
        <div className="area-main-chart">
          <ErrorBoundary>
            <ChartPanel />
          </ErrorBoundary>
        </div>
        <div className="area-bottom-indicators">
          <div className="card-stack">
            <ErrorBoundary>
              <SentimentPanel />
            </ErrorBoundary>
            <div style={{ height: '80px' }}>
              <ErrorBoundary>
                <FearGreed />
              </ErrorBoundary>
            </div>
          </div>
          <ErrorBoundary>
            <BigWhaleMonitor />
          </ErrorBoundary>
          <ErrorBoundary>
            <EventCalendar />
          </ErrorBoundary>
        </div>

        {/* 2. 중앙 사이드바: 성과 + 리포트 */}
        <div className="area-sidebar-1">
          <ErrorBoundary>
            <TradePerformance />
          </ErrorBoundary>
          <div className="flex-grow">
            <ErrorBoundary>
              <ReportPanel data={data} loading={loading} error={error} onRefresh={refetch} />
            </ErrorBoundary>
          </div>
        </div>

        {/* 3. 우측 사이드바: 요약 + 채팅 */}
        <div className="area-sidebar-2">
          <ErrorBoundary>
            <DailyBriefing />
          </ErrorBoundary>
          <div className="flex-grow">
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
