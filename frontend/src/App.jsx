import { Header } from './components/Header'
import { ChartPanel } from './components/ChartPanel'
import { ReportPanel } from './components/ReportPanel'
import { FearGreed } from './components/FearGreed'
import { ChatPanel } from './components/ChatPanel'
import { useStrategy } from './hooks/useStrategy'
import './App.css'

function App() {
  const { data, loading, error, refetch } = useStrategy()

  return (
    <div className="app">
      <Header />
      <div className="main-layout">
        <ChartPanel />
        <div className="right-sidebar">
          <ReportPanel
            data={data}
            loading={loading}
            error={error}
            onRefresh={refetch}
          />
          <FearGreed />
          <ChatPanel />
        </div>
      </div>
    </div>
  )
}

export default App
