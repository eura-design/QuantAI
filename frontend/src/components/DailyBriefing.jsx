import { useState, useEffect } from 'react'
import styles from './DailyBriefing.module.css'
import { API } from '../config'

export function DailyBriefing() {
    const [briefs, setBriefs] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetch(API.DAILY_BRIEF)
            .then(res => res.json())
            .then(data => {
                setBriefs(data)
                setLoading(false)
            })
            .catch(err => {
                console.error("Brief fetch error:", err)
                setLoading(false)
            })
    }, [])

    if (loading) return <div className={styles.loading}>AI 브리핑 생성 중...</div>

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                ✨ 내일의 휴식을 위한 오늘의 체크포인트
            </div>
            <ul className={styles.list}>
                {briefs.map((text, i) => (
                    <li key={i} className={styles.item}>
                        <span className={styles.bullet}>•</span>
                        {text}
                    </li>
                ))}
            </ul>
        </div>
    )
}
