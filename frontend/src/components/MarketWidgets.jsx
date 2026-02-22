import { useState, useEffect } from 'react'
import styles from './MarketWidgets.module.css'
import { API } from '../config'
import { useLanguage } from '../contexts/LanguageContext'

// 1. SentimentPanel
export function SentimentPanel() {
    const { t, lang } = useLanguage()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        fetch(`${API.SENTIMENT}?lang=${lang}`)
            .then(res => res.json())
            .then(d => { setData(d); setLoading(false); })
            .catch(() => setLoading(false))
    }, [lang])

    if (loading || !data) return <div className={styles.loading}>{t('common.loading')}</div>

    return (
        <div className={styles.sentimentContainer}>
            <div className={styles.sentimentResult}>
                <div className={styles.sentimentHeader}>{t('sentiment.title')}</div>
                <div className={styles.sentimentSection}>
                    <div className={styles.sentimentSectionHeader}>
                        <span>{t('sentiment.binance')}</span>
                        <span className={styles.liveTag}>{t('common.live')}</span>
                    </div>
                    <div className={styles.gaugeContainer}>
                        <div className={styles.gaugeLabels}>
                            <span className={styles.longLabel}>{data.binance.long}%</span>
                            <span className={styles.shortLabel}>{data.binance.short}%</span>
                        </div>
                        <div className={styles.barBackground}>
                            <div className={styles.longBar} style={{ width: `${data.binance.long}%` }} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

// 2. FearGreed
export function FearGreed() {
    const { t, lang } = useLanguage()
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        fetch(`${API.FEAR_GREED}?lang=${lang}`)
            .then(res => res.json())
            .then(d => { setData(d); setLoading(false); })
            .catch(() => setLoading(false))
    }, [lang])

    if (loading || !data) return <div className={styles.loading}>{t('common.loading')}</div>

    const value = parseInt(data.value);
    const classification = t(`fearGreed.${data.value_classification.replace(/\s+/g, '')}`) || data.value_classification;

    // 지수에 따른 동적 색상
    const getStatusColor = (val) => {
        if (val <= 25) return '#f43f5e'; // 극도 공포
        if (val <= 45) return '#fb923c'; // 공포
        if (val <= 55) return '#facc15'; // 중립
        if (val <= 75) return '#4ade80'; // 탐욕
        return '#10b981'; // 극도 탐욕
    };

    const statusColor = getStatusColor(value);

    return (
        <div className={styles.fearGreedWidget}>
            <div className={styles.fearGreedTitle}>{t('fearGreed.title')}</div>

            <div className={styles.scoreRow}>
                <span key={value} className={`${styles.scoreNumber} ${styles.flash}`} style={{ color: statusColor }}>{value}</span>
                <span className={styles.scoreText}>{classification}</span>
            </div>

            <div className={styles.progressContainer}>
                <div className={styles.progressTrack}>
                    <div
                        className={styles.progressBar}
                        style={{
                            width: `${value}%`,
                            background: `linear-gradient(90deg, ${statusColor} 0%, ${statusColor}cc 100%)`,
                            boxShadow: `0 0 10px ${statusColor}44`
                        }}
                    />
                </div>
                <div className={styles.labelsRow}>
                    <span>FEAR</span>
                    <span>NEUTRAL</span>
                    <span>GREED</span>
                </div>
            </div>
        </div>
    )
}

// 3. EventCalendar
export function EventCalendar() {
    const { t, lang } = useLanguage()
    const [events, setEvents] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        fetch(`${API.EVENTS}?lang=${lang}`)
            .then(res => res.json())
            .then(d => { setEvents(d); setLoading(false); })
            .catch(() => setLoading(false))
    }, [lang])

    if (loading) return <div className={styles.loading}>{t('common.loading')}</div>

    return (
        <div className={styles.calendarContainer}>
            <div className={styles.calendarTitle}>{t('events.title')}</div>
            <div className={styles.calendarList}>
                {events.map((ev, i) => (
                    <div key={i} className={`${styles.calendarItem} ${styles[ev.impact]}`}>
                        <div className={styles.dDay}>{ev.d_day}</div>
                        <div className={styles.eventInfo}>
                            <div className={styles.eventTitle}>{ev.title}</div>
                            <div className={styles.eventDate}>{ev.date.slice(5)}</div>
                        </div>
                        <div className={styles.impactBadge}>{ev.impact}</div>
                    </div>
                ))}
            </div>
        </div>
    )
}

// 4. DailyBriefing
export function DailyBriefing() {
    const { t, lang } = useLanguage()
    const [briefs, setBriefs] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        fetch(`${API.DAILY_BRIEF}?lang=${lang}`)
            .then(res => res.json())
            .then(d => {
                // 백엔드에서 배열로 오는지 확인 후 저장
                if (Array.isArray(d)) setBriefs(d);
                else if (d.briefs) setBriefs(d.briefs);
                setLoading(false);
            })
            .catch(() => setLoading(false))
    }, [lang])

    if (loading) return (
        <div className={styles.briefingContainer}>
            <div className={styles.briefingHeader}>{t('briefing.title')}</div>
            <div className={styles.loading}>{t('briefing.loading')}</div>
        </div>
    )

    return (
        <div className={styles.briefingContainer}>
            <div className={styles.briefingHeader}>{t('briefing.title')}</div>
            <ul className={styles.briefingList}>
                {(briefs.length > 0 ? briefs : (translations[lang].briefing.placeholders)).map((text, i) => (
                    <li key={i} className={styles.briefingItem}>
                        <span className={styles.briefingBullet}>•</span>
                        {text}
                    </li>
                ))}
            </ul>
        </div>
    )
}

// 5. OasisSummary
export function OasisSummary({ data: strategyData, loading }) {
    const { t } = useLanguage()
    const [data, setData] = useState(null)

    useEffect(() => {
        if (strategyData?.strategy) {
            const jsonMatch = strategyData.strategy.match(/SIGNAL_JSON:\s*```json\s*(\{.*?\})\s*```/s);
            if (jsonMatch) {
                try { setData(JSON.parse(jsonMatch[1])); } catch { }
            }
        }
    }, [strategyData])

    if (loading) return (
        <div className={styles.oasisWrapper}>
            <span className={styles.oasisBadge}>OASIS</span>
            <span className={styles.oasisMessage}>{t('oasis.loading')}</span>
        </div>
    )

    const getMsg = () => {
        if (!data || data.side === 'NONE') return t('oasis.msgNone');
        if (data.side === 'LONG') return t('oasis.msgLong');
        return t('oasis.msgShort');
    };

    return (
        <div className={styles.oasisWrapper}>
            <span className={styles.oasisBadge}>OASIS</span>
            <span className={styles.oasisMessage}>{getMsg()}</span>
        </div>
    )
}

// 218: 6. BigWhaleMonitor
export function BigWhaleMonitor() {
    const { t, lang } = useLanguage()
    const [txs, setTxs] = useState([])

    useEffect(() => {
        const mockTxs = [
            { id: 1, type: 'BUY', amount: '24.5 BTC', time: '12:04', price: '98,421' }, // Whale
            { id: 2, type: 'SELL', amount: '2.5 BTC', time: '12:04', price: '98,415' }, // Shrimp
            { id: 3, type: 'SELL', amount: '6.2 BTC', time: '12:05', price: '98,390' },  // Shark
            { id: 4, type: 'BUY', amount: '0.8 BTC', time: '12:05', price: '98,400' },  // Shrimp
            { id: 5, type: 'BUY', amount: '12.1 BTC', time: '12:05', price: '98,405' }, // Whale
            { id: 6, type: 'BUY', amount: '8.2 BTC', time: '12:06', price: '98,410' },  // Shark
        ];
        // 최신순으로 정렬 (id 역순)
        setTxs(mockTxs.reverse());
    }, [lang])

    return (
        <div className={styles.whaleContainer}>
            <div className={styles.whaleHeader}>
                {t('whale.title')}
                <span className={`${styles.whaleStatusBadge} ${styles.statusOn}`}>{t('whale.status')}</span>
            </div>
            <div className={styles.whaleList}>
                {txs.map(tx => {
                    const amountValue = parseFloat(tx.amount);
                    let emoji = '🦐'; // 1~4 (Shrimp)
                    if (amountValue >= 10) {
                        emoji = '🐋'; // 10+ (Whale)
                    } else if (amountValue >= 5) {
                        emoji = '🦈'; // 5~9 (Shark)
                    }

                    return (
                        <div key={tx.id} className={styles.whaleRow}>
                            <span className={tx.type === 'BUY' ? styles.whaleBuy : styles.whaleSell}>
                                {emoji} {tx.type} {tx.amount}
                            </span>
                            <span className={styles.whaleTime}>{tx.time}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    )
}
