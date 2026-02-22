import { useState, useEffect } from 'react'
import styles from './Header.module.css'
import { NewsTicker } from './NewsTicker'
import { useLanguage } from '../contexts/LanguageContext'

export function Header() {
    const { lang, setLang, t } = useLanguage()
    const [wsStatus, setWsStatus] = useState(t('header.connecting'))
    const [isLive, setIsLive] = useState(false)
    const [interval, setInterval] = useState('')

    useEffect(() => {
        const wsHandler = (e) => {
            setWsStatus(e.detail.text)
            setIsLive(e.detail.live)
        }
        const tfHandler = (e) => {
            const suffix = t('header.candleSuffix')
            setInterval(e.detail.label + suffix)
        }

        // 언어 변경 시 현재 상태 문구가 기본값이면 즉시 번역
        setWsStatus(prev => (prev === '연결 중...' || prev === 'Connecting...') ? t('header.connecting') : prev);

        window.addEventListener('ws-status-change', wsHandler)
        window.addEventListener('timeframe-change', tfHandler)
        return () => {
            window.removeEventListener('ws-status-change', wsHandler)
            window.removeEventListener('timeframe-change', tfHandler)
        }
    }, [lang, t])

    return (
        <>
            <NewsTicker />
            <header className={styles.header}>
                <div className={styles.logo}>
                    <span className={styles.dot} />
                    <span className={styles.logoText}>
                        Quant<em>AI</em>
                    </span>
                    <span className={styles.subtitle}>{t('header.subtitle')}</span>
                </div>

                <div className={styles.center}>
                    <span className={styles.pair}>BTC / USDT</span>
                    <span className={styles.interval}>{interval}</span>
                </div>

                <div className={styles.rightActions}>
                    <div className={styles.langSwitch}>
                        <button
                            className={`${styles.langBtn} ${lang === 'ko' ? styles.active : ''}`}
                            onClick={() => setLang('ko')}
                        >
                            KR
                        </button>
                        <button
                            className={`${styles.langBtn} ${lang === 'en' ? styles.active : ''}`}
                            onClick={() => setLang('en')}
                        >
                            EN
                        </button>
                    </div>

                    <div className={`${styles.status} ${isLive ? styles.live : styles.offline}`}>
                        <span className={styles.statusDot} />
                        {wsStatus}
                    </div>
                </div>
            </header>
        </>
    )
}
