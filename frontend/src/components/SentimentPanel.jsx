import { useState, useEffect } from 'react'
import styles from './SentimentPanel.module.css'
import { API } from '../config'

export function SentimentPanel() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)

    const fetchSentiment = async () => {
        try {
            const res = await fetch(API.SENTIMENT)
            const json = await res.json()
            setData(json)
        } catch (err) {
            console.error("Sentiment fetch error:", err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchSentiment()
        const timer = setInterval(fetchSentiment, 30000) // 30초마다 갱신
        return () => clearInterval(timer)
    }, [])

    if (loading || !data) return <div className={styles.loading}>분석 중...</div>

    const { target, binance, votes } = data
    // binance는 {long: 51.2, short: 48.8} 형태
    const longP = binance ? binance.long : 50
    const shortP = binance ? binance.short : 50

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                📊 실시간 시장 심리 (롱/숏)
            </div>

            <div className={styles.gaugeContainer}>
                <div className={styles.labels}>
                    <span className={styles.longLabel}>LONG {longP}%</span>
                    <span className={styles.shortLabel}>{shortP}% SHORT</span>
                </div>
                <div className={styles.barBackground}>
                    <div
                        className={styles.longBar}
                        style={{ width: `${longP}%` }}
                    />
                </div>
            </div>

            <div className={styles.voteStatus}>
                <div className={styles.voteTitle}>커뮤니티 투표 현황</div>
                <div className={styles.voteStats}>
                    <span className={styles.bullText}>Bull: {votes.bull}</span>
                    <span className={styles.bearText}>Bear: {votes.bear}</span>
                </div>
            </div>
        </div>
    )
}
