import { useState, useEffect } from 'react'
import styles from './OasisSummary.module.css'
import { API } from '../config'

export function OasisSummary() {
    const [summary, setSummary] = useState("시장의 흐름을 분석하고 있습니다. 잠시만 기다려주세요...")

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                const res = await fetch(API.STRATEGY)
                const data = await res.json()

                // 간단한 규칙 기반으로 따뜻한 한 문장 요약 생성 (백엔드 로직에 따라 다름)
                if (data.strategy.includes("LONG")) {
                    setSummary("데이터는 긍정적인 신호를 보내고 있습니다. 차분하게 기회를 포착해 보세요. ✨")
                } else if (data.strategy.includes("SHORT")) {
                    setSummary("시장 기류가 다소 차가워졌습니다. 서두르지 말고 안전한 구간을 기다리세요. 🛡️")
                } else {
                    setSummary("지금은 무리한 매매보다 따뜻한 차 한 잔과 함께 관망하기 좋은 시점입니다. 🍵")
                }
            } catch (err) {
                setSummary("시장의 고요함을 즐기며 다음 기회를 기다려 보세요. 🍃")
            }
        }

        fetchSummary()
        const timer = setInterval(fetchSummary, 60000)
        return () => clearInterval(timer)
    }, [])

    return (
        <div className={styles.wrapper}>
            <div className={styles.oasisBadge}>OASIS BRIEF</div>
            <div className={styles.content}>
                <span className={styles.message}>{summary}</span>
            </div>
        </div>
    )
}
