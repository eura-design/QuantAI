import { useState, useEffect } from 'react'
import styles from './SentimentPanel.module.css'
import { API } from '../config'

export function SentimentPanel() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    // 로컬 스토리지에서 투표 여부 확인
    const [voted, setVoted] = useState(() => {
        return localStorage.getItem('voted_sentiment') === 'true'
    })

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

    const handleVote = async (side) => {
        if (voted) return
        try {
            await fetch(API.VOTE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ side })
            })
            setVoted(true)
            localStorage.setItem('voted_sentiment', 'true')
            fetchSentiment()
        } catch (err) {
            console.error("Vote error:", err)
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

    const totalVotes = votes.bull + votes.bear
    const bullP = totalVotes > 0 ? Math.round((votes.bull / totalVotes) * 100) : 50
    const bearP = 100 - bullP

    return (
        <div className={styles.container}>
            {!voted ? (
                /* 투표 전: 컴팩트한 투표 버튼만 표시 */
                <div className={styles.initialState}>
                    <div className={styles.headerCompact}>
                        <span className={styles.icon}>🔮</span> 참여형 시장 심리
                    </div>
                    <div className={styles.subTitle}>오늘 비트코인의 방향은?</div>
                    <div className={styles.voteButtons}>
                        <button className={styles.bullBtnBig} onClick={() => handleVote('bull')}>
                            <span className={styles.btnIcon}>🚀</span> 상승
                        </button>
                        <button className={styles.bearBtnBig} onClick={() => handleVote('bear')}>
                            <span className={styles.btnIcon}>📉</span> 하락
                        </button>
                    </div>
                    <p className={styles.hintText}>투표를 완료하면 실시간 심리 지표가 공개됩니다.</p>
                </div>
            ) : (
                /* 투표 후: 모든 데이터 공개 */
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
                            <span>커뮤니티 투표 결과</span>
                            <span className={styles.timerTag}>4h reset</span>
                        </div>
                        <div className={styles.gaugeContainer}>
                            <div className={styles.labels}>
                                <span className={styles.bullText}>BULL {bullP}%</span>
                                <span className={styles.bearText}>{bearP}% BEAR</span>
                            </div>
                            <div className={styles.barBackgroundUser}>
                                <div className={styles.bullBar} style={{ width: `${bullP}%` }} />
                            </div>
                        </div>
                        <div className={styles.voteFooter}>
                            총 {totalVotes}명 참여 완료
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
