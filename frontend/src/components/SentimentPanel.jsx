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
        const timer = setInterval(fetchSentiment, 30000)
        return () => clearInterval(timer)
    }, [])

    if (loading || !data) return <div className={styles.loading}>데이터 로드 중...</div>

    const { binance } = data
    const longP = binance ? binance.long : 50
    const shortP = binance ? binance.short : 50

    return (
        <div className={styles.container}>
            <div className={styles.resultState}>
                <div className={styles.header}>
                    📊 실시간 시장 심리 리포트
                </div>

                <div className={styles.section}>
                    <div className={styles.sectionHeader}>
                        <span>바이낸스 선물 포지션</span>
                        <span className={styles.liveTag}>LIVE</span>
                    </div>
                    <div className={styles.gaugeContainer}>
                        <div className={styles.labels}>
                            <span className={styles.longLabel}>LONG {longP}%</span>
                            <span className={styles.shortLabel}>{shortP}% SHORT</span>
                        </div>
                        <div className={styles.barBackground}>
                            <div className={styles.longBar} style={{ width: `${longP}%` }} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
