import { useState, useEffect } from 'react'
import styles from './TradePerformance.module.css'
import { API } from '../config'

export function TradePerformance() {
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)

    const fetchStats = async () => {
        try {
            const res = await fetch(`${API.BASE_URL}/api/trades/stats`)
            const data = await res.json()
            setStats(data)
        } catch (err) {
            console.error("Stats fetch error:", err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchStats()
        const timer = setInterval(fetchStats, 60000) // 1분마다 갱신
        return () => clearInterval(timer)
    }, [])

    if (loading || !stats) return <div className={styles.loading}>성과 집계 중...</div>

    const { wins, losses, win_rate, history } = stats

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <span className={styles.badge}>TRACK RECORD</span>
                <h3 className={styles.title}>AI 가상 매매 성과</h3>
            </div>

            <div className={styles.statsGrid}>
                <div className={styles.statItem}>
                    <div className={styles.statValue}>{win_rate}%</div>
                    <div className={styles.statLabel}>승률</div>
                </div>
                <div className={styles.statItem}>
                    <div className={styles.statValue}>{wins}승</div>
                    <div className={styles.statLabel}>수익</div>
                </div>
                <div className={styles.statItem}>
                    <div className={styles.statValue}>{losses}패</div>
                    <div className={styles.statLabel}>손실</div>
                </div>
            </div>

            <div className={styles.historySection}>
                <h4 className={styles.historyTitle}>최근 매매 기록</h4>
                <div className={styles.historyList}>
                    {history.length === 0 ? (
                        <div className={styles.empty}>진행 중인 매매가 없습니다.</div>
                    ) : (
                        history.map((trade) => (
                            <div key={trade.id} className={styles.tradeRow}>
                                <div className={`${styles.side} ${styles[trade.side.toLowerCase()]}`}>
                                    {trade.side}
                                </div>
                                <div className={styles.tradeInfo}>
                                    <div className={styles.entryPrice}>@{trade.entry.toLocaleString()}</div>
                                    <div className={styles.timestamp}>{new Date(trade.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                                </div>
                                <div className={`${styles.status} ${styles[trade.status.toLowerCase()]}`}>
                                    {trade.status === 'OPEN' ? '진행중' : trade.status}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    )
}
