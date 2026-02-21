import { useState, useEffect } from 'react'
import styles from './Header.module.css'
import { NewsTicker } from './NewsTicker'

export function Header() {
    const [wsStatus, setWsStatus] = useState('연결 중...')
    const [isLive, setIsLive] = useState(false)

    const [interval, setInterval] = useState('5분봉')

    useEffect(() => {
        const wsHandler = (e) => {
            setWsStatus(e.detail.text)
            setIsLive(e.detail.live)
        }
        const tfHandler = (e) => {
            setInterval(e.detail.label + '봉')
        }
        window.addEventListener('ws-status-change', wsHandler)
        window.addEventListener('timeframe-change', tfHandler)
        return () => {
            window.removeEventListener('ws-status-change', wsHandler)
            window.removeEventListener('timeframe-change', tfHandler)
        }
    }, [])

    return (
        <>
            <NewsTicker />
            <header className={styles.header}>
                <div className={styles.logo}>
                    <span className={styles.dot} />
                    <span className={styles.logoText}>
                        Quant<em>AI</em>
                    </span>
                    <span className={styles.badge}>BETA</span>
                </div>

                <div className={styles.center}>
                    <span className={styles.pair}>BTC / USDT</span>
                    <span className={styles.interval}>{interval}</span>
                </div>

                <div className={`${styles.status} ${isLive ? styles.live : styles.offline}`}>
                    <span className={styles.statusDot} />
                    {wsStatus}
                </div>
            </header>
        </>
    )
}
