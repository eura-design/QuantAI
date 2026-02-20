import { useState, useEffect } from 'react'
import styles from './WhaleTracker.module.css'
import { API } from '../config'

export function WhaleTracker() {
    const [alerts, setAlerts] = useState([])

    useEffect(() => {
        const eventSource = new EventSource(API.WHALE_STREAM)

        eventSource.onmessage = (e) => {
            try {
                const whale = JSON.parse(e.data)
                setAlerts(prev => [whale, ...prev].slice(0, 15)) // 최신 15개 유지
            } catch (err) {
                console.error("Whale Alert Error:", err)
            }
        }

        eventSource.onerror = () => {
            eventSource.close()
        }

        return () => eventSource.close()
    }, [])

    const formatAmount = (amt) => {
        if (amt >= 1000000) return (amt / 1000000).toFixed(2) + 'M'
        return (amt / 1000).toFixed(0) + 'K'
    }

    const getIcon = (amt) => {
        if (amt >= 1000000) return '🐋'
        if (amt >= 500000) return '🦈'
        return '🐟'
    }

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <span className={styles.title}>🐋 실시간 고래 추적</span>
                <span className={styles.badge}>LIVE</span>
            </div>
            <div className={styles.list}>
                {alerts.length === 0 ? (
                    <div className={styles.empty}>대형 체결을 감시 중입니다...</div>
                ) : (
                    alerts.map((a, i) => (
                        <div key={a.id || i} className={`${styles.item} ${styles[a.side.toLowerCase()]}`}>
                            <span className={styles.icon}>{getIcon(a.amount)}</span>
                            <div className={styles.info}>
                                <div className={styles.mainInfo}>
                                    <span className={styles.side}>{a.side === 'BUY' ? '매수' : '매도'}</span>
                                    <span className={styles.amount}>${formatAmount(a.amount)}</span>
                                </div>
                                <div className={styles.subInfo}>
                                    <span>{a.qty.toFixed(3)} BTC</span>
                                    <span>@{a.price.toLocaleString()}</span>
                                </div>
                            </div>
                            <span className={styles.time}>{a.timestamp}</span>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}
