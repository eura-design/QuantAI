import { useState } from 'react'
import styles from './BullBearVote.module.css'
import { API } from '../config'

export function BullBearVote() {
    const [voted, setVoted] = useState(false)

    const handleVote = async (side) => {
        if (voted) return
        try {
            await fetch(API.VOTE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ side })
            })
            setVoted(true)
            // 투표 후 전역적으로 상태를 알리고 싶다면 CustomEvent 등을 쓸 수 있지만,
            // 여기선 간단히 로컬 상태만 변경
        } catch (err) {
            console.error("Vote error:", err)
        }
    }

    return (
        <div className={styles.container}>
            <div className={styles.title}>내 생각은?</div>
            {voted ? (
                <div className={styles.votedMessage}>투표 완료! 결과는 실시간 심리 지표에서 확인하세요.</div>
            ) : (
                <div className={styles.buttonGroup}>
                    <button
                        className={styles.bullBtn}
                        onClick={() => handleVote('bull')}
                    >
                        🚀 상승 (Bull)
                    </button>
                    <button
                        className={styles.bearBtn}
                        onClick={() => handleVote('bear')}
                    >
                        📉 하락 (Bear)
                    </button>
                </div>
            )}
        </div>
    )
}
