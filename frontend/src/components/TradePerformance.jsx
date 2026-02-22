import { useState, useEffect } from 'react'
import styles from './TradePerformance.module.css'
import { API } from '../config'
import { useLanguage } from '../contexts/LanguageContext'

export function TradePerformance() {
    const { t, lang } = useLanguage()
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        fetch(`${API.TRADES_STATS}?lang=${lang}`)
            .then(res => res.json())
            .then(d => {
                setStats(d)
                setLoading(false)
            })
            .catch(() => setLoading(false))
    }, [lang])

    if (loading || !stats) return <div className={styles.loading}>{t('performance.loading')}</div>

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div className={styles.headerTitleGroup}>
                    <div className={styles.badge}>{t('common.live')}</div>
                    <div className={styles.title}>{t('performance.title')}</div>
                    {stats.current_status && (
                        <div className={`${styles.statusBadge} ${styles[stats.current_status.toLowerCase()]}`}>
                            <span className={styles.pulseDot}></span>
                            {t(`performance.status_labels.${stats.current_status}`)}
                        </div>
                    )}
                </div>
            </div>

            <div className={styles.statsGrid}>
                <div className={styles.statItem}>
                    <div className={styles.statValue}>{stats.win_rate}%</div>
                    <div className={styles.statLabel}>{t('performance.winRate')}</div>
                </div>
                <div className={styles.statItem}>
                    <div className={styles.statValue}>{stats.wins}</div>
                    <div className={styles.statLabel}>{t('performance.wins')}</div>
                </div>
                <div className={styles.statItem}>
                    <div className={styles.statValue}>{stats.losses}</div>
                    <div className={styles.statLabel}>{t('performance.losses')}</div>
                </div>
            </div>
        </div>
    )
}
