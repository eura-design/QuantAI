import { Header } from './components/Header'
import { ChartPanel } from './components/ChartPanel'
import { ReportPanel } from './components/ReportPanel'
import { FearGreed } from './components/FearGreed'
import { WhaleTracker } from './components/WhaleTracker'
import { EventCalendar } from './components/EventCalendar'
import { ChatPanel } from './components/ChatPanel'
import ErrorBoundary from './components/ErrorBoundary'
import { useStrategy } from './hooks/useStrategy'
import './App.css'

function App() {
  const { data, loading, error, refetch } = useStrategy()

  return (
    <div className="app">
      <Header />
      <div className="main-layout">
        <ErrorBoundary>
          <ChartPanel />
        </ErrorBoundary>

        {/* 제1 사이드바: 분석 및 심리 */}
        <div className="sidebar-column">
          <ErrorBoundary>
            <ReportPanel
              data={data}
              loading={loading}
              error={error}
              onRefresh={refetch}
            />
          </ErrorBoundary>

          <ErrorBoundary>
            <WhaleTracker />
          </ErrorBoundary>

          <ErrorBoundary>
            <FearGreed />
          </ErrorBoundary>
        </div>

        {/* 제2 사이드바: 일정 및 채팅 */}
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
