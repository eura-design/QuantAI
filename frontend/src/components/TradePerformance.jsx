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

        </div>
    )
}
