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

// 🐋 실시간 고래 감시 컴포넌트 (높이 조절을 위해 별도 스타일 제거 및 Container화)
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
        ws.onopen = () => {
          if (active) {
            setStatus('ON');
            window.dispatchEvent(new CustomEvent('ws-status-change', { detail: { text: 'LIVE · 고래 추적 중', live: true } }));
          }
        }
        ws.onmessage = (e) => {
          if (!active) return;
          try {
            const m = JSON.parse(e.data);
            const amount = parseFloat(m.p) * parseFloat(m.q);
            if (amount >= 50000) {
              let tier = "SHRIMP";
              if (amount >= 500000) tier = "KRAKEN";
              else if (amount >= 100000) tier = "WHALE";
              else if (amount >= 30000) tier = "DOLPHIN";

              const alert = {
                tier,
                side: m.m ? "SELL" : "BUY",
                amount: amount,
                qty: parseFloat(m.q),
                timestamp: new Date(m.T).toTimeString().slice(0, 8)
              };
              setMsgs(p => [alert, ...p].slice(0, 30));
            }
          } catch (err) { }
        }
        ws.onerror = () => { if (active) setStatus('OFF'); }
        ws.onclose = () => {
          if (active) {
            setStatus('OFF');
            window.dispatchEvent(new CustomEvent('ws-status-change', { detail: { text: '연결 끊김 · 재연결 중', live: false } }));
            setTimeout(connect, 5000);
          }
        }
      } catch (e) { }
    };

    connect();
    return () => {
      active = false;
      if (ws) ws.close();
    }
  }, []);

  return (
    <div style={{
      height: '100%', display: 'flex', flexDirection: 'column',
      background: '#0d1117', border: '1px solid #1e2d45', borderRadius: '12px',
      overflow: 'hidden'
    }}>
      <div style={{
        padding: '10px 15px', background: '#131c2e',
        borderBottom: '1px solid #1e2d45', display: 'flex',
        justifyContent: 'space-between', alignItems: 'center'
      }}>
        <span style={{ color: '#94a3b8', fontSize: '12px', fontWeight: 'bold' }}>🐋 실시간 고래 감시</span>
        <span style={{ fontSize: '10px', color: status === 'ON' ? '#26a69a' : '#ef5350' }}>{status}</span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
        {msgs.length === 0 ? (
          <div style={{ color: '#475569', textAlign: 'center', fontSize: '11px', padding: '20px 0' }}>대기 중...</div>
        ) : (
          msgs.map((m, i) => (
            <div key={i} style={{
              padding: '6px 10px', marginBottom: '6px',
              background: m.side === 'BUY' ? 'rgba(38,166,154,0.03)' : 'rgba(239,83,80,0.03)',
              borderRadius: '4px', border: '1px solid #1e2d45',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center'
            }}>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ fontSize: '14px' }}>{m.tier === 'WHALE' ? '🐋' : m.tier === 'KRAKEN' ? '🐙' : '🐬'}</span>
                <div>
                  <div style={{ color: m.side === 'BUY' ? '#26a69a' : '#ef5350', fontSize: '10px', fontWeight: 'bold' }}>{m.side}</div>
                  <div style={{ color: '#fff', fontSize: '12px', fontWeight: 'bold' }}>${(m.amount / 1000).toFixed(1)}K</div>
                </div>
              </div>
              <div style={{ color: '#475569', fontSize: '9px' }}>{m.timestamp}</div>
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
        {/* ROW 1 */}
        <div className="area-top-left">
          <ErrorBoundary>
            <ChartPanel />
          </ErrorBoundary>
        </div>

        <div className="area-top-mid">
          <div className="grid-cell">
            <ErrorBoundary>
              <TradePerformance />
            </ErrorBoundary>
            <div className="scroll-container">
              <ErrorBoundary>
                <ReportPanel data={data} loading={loading} error={error} onRefresh={refetch} />
              </ErrorBoundary>
            </div>
          </div>
        </div>

        <div className="area-top-right">
          <div className="grid-cell">
            <ErrorBoundary>
              <DailyBriefing />
            </ErrorBoundary>
            <div className="scroll-container">
              <ErrorBoundary>
                <ChatPanel />
              </ErrorBoundary>
            </div>
          </div>
        </div>

        {/* ROW 2 */}
        <div className="area-bot-left">
          <div className="grid-cell" style={{ flexDirection: 'row', gap: '12px' }}>
            <div style={{ flex: 1.5 }}>
              <ErrorBoundary>
                <SentimentPanel />
              </ErrorBoundary>
            </div>
            <div style={{ flex: 1 }}>
              <ErrorBoundary>
                <FearGreed />
              </ErrorBoundary>
            </div>
          </div>
        </div>

        <div className="area-bot-mid">
          <ErrorBoundary>
            <BigWhaleMonitor />
          </ErrorBoundary>
        </div>

        <div className="area-bot-right">
          <ErrorBoundary>
            <EventCalendar />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  )
}

export default App
