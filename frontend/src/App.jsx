import { Header } from './components/Header'
import { ChartPanel } from './components/ChartPanel'
import { ReportPanel } from './components/ReportPanel'
import { ChatPanel } from './components/ChatPanel'
import { TradePerformance } from './components/TradePerformance'
import { SentimentPanel, FearGreed, DailyBriefing, EventCalendar, OasisSummary, BigWhaleMonitor } from './components/MarketWidgets'
import ErrorBoundary from './components/ErrorBoundary'
import { useStrategy } from './hooks/useStrategy'
import { LanguageProvider, useLanguage } from './contexts/LanguageContext'
import './App.css'

function AppContent() {
  const { lang } = useLanguage()
  const { data, loading, error, refetch } = useStrategy(lang)

  return (
    <div className="app">
      <Header />
      <OasisSummary data={data} loading={loading} />

      <div className="main-layout">
        {/* 1열: 차트 + 하단 지표 3세트 */}
        <div className="col-main">
          <div className="col-main-top">
            <ErrorBoundary>
              <ChartPanel />
            </ErrorBoundary>
          </div>

          <div className="col-main-bottom">
            <div className="indicator-stack">
              <div className="indicator-box">
                <ErrorBoundary>
                  <SentimentPanel />
                </ErrorBoundary>
              </div>
              <div className="indicator-box">
                <ErrorBoundary>
                  <FearGreed />
                </ErrorBoundary>
              </div>
            </div>

            <div className="flex-column">
              <ErrorBoundary>
                <BigWhaleMonitor />
              </ErrorBoundary>
            </div>

            <div className="flex-column">
              <ErrorBoundary>
                <EventCalendar />
              </ErrorBoundary>
            </div>
          </div>
        </div>

        {/* 2열: 성과 + 리포트 */}
        <div className="area-sidebar-1 sidebar-container">
          <div className="fixed-height-180 flex-column">
            <ErrorBoundary>
              <TradePerformance />
            </ErrorBoundary>
          </div>
          <div className="flex-grow flex-column">
            <ErrorBoundary>
              <ReportPanel data={data} loading={loading} error={error} onRefresh={refetch} />
            </ErrorBoundary>
          </div>
        </div>

        {/* 3열: 뉴스 요약 + 채팅 */}
        <div className="area-sidebar-2 sidebar-container">
          <div className="fixed-height-180 flex-column">
            <ErrorBoundary>
              <DailyBriefing />
            </ErrorBoundary>
          </div>
          <div className="flex-grow flex-column">
            <ErrorBoundary>
              <ChatPanel />
            </ErrorBoundary>
          </div>
        </div>
      </div>
    </div>
  )
}

function App() {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  )
}

export default App
