import { useState, useEffect } from 'react'
import styles from './WhaleTracker.module.css'
import { API } from '../config.js'

export function WhaleTracker() {
    const [alerts, setAlerts] = useState([])

    useEffect(() => {
        let eventSource;
        try {
            eventSource = new EventSource(API.WHALE_STREAM)

            eventSource.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data)
                    if (data && typeof data === 'object') {
                        setAlerts(prev => [data, ...prev].slice(0, 20))
                    }
                } catch (err) {
                    console.error("Whale Parse Error:", err)
                }
            }

            eventSource.onerror = (e) => {
                console.error("Whale SSE Error:", e)
                if (eventSource) eventSource.close()
            }
        } catch (err) {
            console.error("Whale EventSource Error:", err)
        }

        return () => {
            if (eventSource) eventSource.close()
        }
    }, [])

    const formatAmount = (amt) => {
        const n = Number(amt)
        if (isNaN(n)) return '0K'
        if (n >= 1000000) return (n / 1000000).toFixed(2) + 'M'
        if (n >= 1000) return (n / 1000).toFixed(0) + 'K'
        return n.toFixed(0)
    }

    const getIcon = (amt) => {
        const n = Number(amt)
        if (n >= 1000000) return '🐋'
        if (n >= 500000) return '🦈'
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
                    alerts.map((a, i) => {
                        // 극도로 안전한 렌더링
                        if (!a || typeof a !== 'object') return null;

                        // 시스템 메시지 처리
                        if (a.type === 'system') {
                            return (
                                <div key={i} className={styles.systemMessage}>
                                    <span>{String(a.text || '')}</span>
                                    <span className={styles.time}>{String(a.timestamp || '')}</span>
                                </div>
                            )
                        }

                        // 일반 거래(고래) 데이터 처리
                        const side = String(a.side || '').toUpperCase()
                        const sideClass = side === 'BUY' ? 'buy' : side === 'SELL' ? 'sell' : ''
                        const sideLabel = side === 'BUY' ? '매수' : side === 'SELL' ? '매도' : side

                        return (
                            <div key={a.id || i} className={`${styles.item} ${styles[sideClass] || ''}`}>
                                <span className={styles.icon}>{getIcon(a.amount)}</span>
                                <div className={styles.info}>
                                    <div className={styles.mainInfo}>
                                        <span className={styles.side}>{sideLabel}</span>
                                        <span className={styles.amount}>${formatAmount(a.amount)}</span>
                                    </div>
                                    <div className={styles.subInfo}>
                                        <span>{Number(a.qty || 0).toFixed(3)} BTC</span>
                                        <span>@{Number(a.price || 0).toLocaleString()}</span>
                                    </div>
                                </div>
                                <span className={styles.time}>{String(a.timestamp || '')}</span>
                            </div>
                        )
                    })
                )}
            </div>
        </div>
    )
}
