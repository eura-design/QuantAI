import { useState, useEffect } from 'react'
import { Header } from './components/Header'
import { ChartPanel } from './components/ChartPanel'
import { ReportPanel } from './components/ReportPanel'
import { FearGreed } from './components/FearGreed'
import { EventCalendar } from './components/EventCalendar'
import { ChatPanel } from './components/ChatPanel'
import { SentimentPanel } from './components/SentimentPanel'
import { DailyBriefing } from './components/DailyBriefing'
import { BullBearVote } from './components/BullBearVote'
import ErrorBoundary from './components/ErrorBoundary'
import { useStrategy } from './hooks/useStrategy'
import { API } from './config'
import './App.css'

// 🐋 새로운 이름과 극단적으로 단순한 구조 (에러 방지용)
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
            // m.p: 가격, m.q: 수량
            const amount = parseFloat(m.p) * parseFloat(m.q);

            // $50,000 이상인 경우에만 처리
            if (amount >= 50000) {
              let tier = "SHRIMP";
              if (amount >= 500000) tier = "KRAKEN";
              else if (amount >= 100000) tier = "WHALE";
              else if (amount >= 30000) tier = "DOLPHIN";

              const alert = {
                tier,
                side: m.m ? "SELL" : "BUY", // m은 'Is the buyer the market maker?'
                amount: amount,
                qty: parseFloat(m.q),
                timestamp: new Date(m.T).toTimeString().slice(0, 8)
              };
              setMsgs(p => [alert, ...p].slice(0, 50));
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
          msgs.map((m, i) => {
            if (!m) return null;
            const tierMap = {
              'SHRIMP': { icon: '🦐', name: '새우' },
              'DOLPHIN': { icon: '🐬', name: '돌고래' },
              'WHALE': { icon: '🐋', name: '고래' },
              'KRAKEN': { icon: '🐙', name: '크라켄' },
              'SYSTEM': { icon: '🤖', name: '알림' }
            };
            const info = tierMap[m.tier] || tierMap[m.type] || { icon: '🐋', name: m.side === 'BUY' ? '매수' : '매도' };

            return (
              <div key={i} style={{
                padding: '10px', marginBottom: '8px',
                background: m.side === 'BUY' ? 'rgba(38,166,154,0.05)' : 'rgba(239,83,80,0.05)',
                borderRadius: '4px', border: '1px solid #1e2d45',
                display: 'flex', justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <span style={{ fontSize: '20px' }}>{info.icon}</span>
                  <div>
                    <div style={{ color: m.side === 'BUY' ? '#26a69a' : '#ef5350', fontSize: '11px', fontWeight: 'bold' }}>
                      {info.name} • {m.side === 'BUY' ? '매수' : m.side === 'SELL' ? '매도' : '알림'}
                    </div>
                    <div style={{ color: '#fff', fontSize: '14px', fontWeight: 'bold', marginTop: '2px' }}>
                      ${Number(m.amount || 0) > 0 ? (Number(m.amount) / 1000).toFixed(1) + 'K' : 'SYSTEM'}
                    </div>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ color: '#475569', fontSize: '10px' }}>{m.timestamp || '--:--:--'}</div>
                  {m.qty && <div style={{ color: '#64748b', fontSize: '10px' }}>{Number(m.qty).toFixed(2)} BTC</div>}
                </div>
              </div>
            );
          })
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
            <DailyBriefing />
          </ErrorBoundary>

          <ErrorBoundary>
            <ReportPanel data={data} loading={loading} error={error} onRefresh={refetch} />
          </ErrorBoundary>

          <ErrorBoundary>
            <BigWhaleMonitor />
          </ErrorBoundary>
        </div>

        <div className="sidebar-column">
          <ErrorBoundary>
            <SentimentPanel />
          </ErrorBoundary>

          <ErrorBoundary>
            <BullBearVote />
          </ErrorBoundary>

          <ErrorBoundary>
            <FearGreed />
          </ErrorBoundary>

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
