import { useState, useEffect } from 'react'
import styles from './Header.module.css'
import { NewsTicker } from './NewsTicker'

export function Header() {
    const [wsStatus, setWsStatus] = useState('연결 중...')
    const [isLive, setIsLive] = useState(false)

    useEffect(() => {
        const handler = (e) => {
            setWsStatus(e.detail.text)
            setIsLive(e.detail.live)
        }
        window.addEventListener('ws-status-change', handler)
        return () => window.removeEventListener('ws-status-change', handler)
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
                    <span className={styles.interval}>5분봉</span>
                </div>

                <div className={`${styles.status} ${isLive ? styles.live : styles.offline}`}>
                    <span className={styles.statusDot} />
                    {wsStatus}
                </div>
            </header>
        </>
    )
}
