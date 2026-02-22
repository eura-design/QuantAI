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

    const { binance, votes } = data
    const longP = binance ? binance.long : 50
    const shortP = binance ? binance.short : 50

    const bullP = votes && votes.total > 0 ? Math.round((votes.bull / votes.total) * 100) : 50
    const bearP = 100 - bullP

    const handleVote = async (side) => {
        try {
            const res = await fetch(API.VOTE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ side })
            })
            const newVotes = await res.json()
            setData(prev => ({ ...prev, votes: newVotes }))
        } catch (err) {
            console.error("Vote error:", err)
        }
    }

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

                <div className={styles.divider} />

                <div className={styles.section}>
                    <div className={styles.sectionHeader}>
                        <span>커뮤니티 심리 (오늘)</span>
                        <span className={styles.timerTag}>{votes?.total || 0}명 참여</span>
                    </div>
                    <div className={styles.gaugeContainer}>
                        <div className={styles.labels}>
                            <span className={styles.longLabel}>BULL {bullP}%</span>
                            <span className={styles.shortLabel}>{bearP}% BEAR</span>
                        </div>
                        <div className={styles.barBackground}>
                            <div className={styles.bullBar} style={{ width: `${bullP}%` }} />
                        </div>
                    </div>
                    <div className={styles.voteButtons}>
                        <button className={styles.bullBtnBig} onClick={() => handleVote('bull')}>BULL 🚀</button>
                        <button className={styles.bearBtnBig} onClick={() => handleVote('bear')}>BEAR 📉</button>
                    </div>
                </div>
            </div>
        </div>
    )
}
