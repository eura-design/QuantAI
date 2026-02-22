import { useState, useEffect } from 'react'
import styles from './MarketWidgets.module.css'
import { API } from '../config'

// 1. Sentiment Panel
export function SentimentPanel() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)

    const fetchSentiment = async () => {
        try {
            const res = await fetch(API.SENTIMENT)
            const json = await res.json()
            setData(json)
        } catch (err) {
            console.error("Sentiment fetch error:", err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchSentiment()
        const timer = setInterval(fetchSentiment, 30000)
        return () => clearInterval(timer)
    }, [])

    if (loading || !data) return <div className={styles.loading}>데이터 로드 중...</div>

    const { binance } = data
    const longP = binance ? binance.long : 50
    const shortP = binance ? binance.short : 50

    return (
        <div className={styles.sentimentContainer}>
            <div className={styles.sentimentResult}>
                <div className={styles.sentimentHeader}>
                    🌱 시장 참여자들의 정서적 발걸음
                </div>

                <div className={styles.sentimentSection}>
                    <div className={styles.sentimentSectionHeader}>
                        <span>바이낸스 선물 포지션 심리</span>
                        <span className={styles.liveTag}>LIVE</span>
                    </div>
                    <div className={styles.gaugeContainer}>
                        <div className={styles.gaugeLabels}>
                            <span className={styles.longLabel}>LONG {longP}%</span>
                            <span className={styles.shortLabel}>{shortP}% SHORT</span>
                        </div>
                        <div className={styles.barBackground}>
                            <div className={styles.longBar} style={{ width: `${longP}%` }} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

// 2. Fear & Greed
export function FearGreed() {
    const [data, setData] = useState({ value: '50', value_classification: 'Neutral' })

    useEffect(() => {
        fetch(API.FEAR_GREED)
            .then(r => r.json())
            .then(d => {
                if (d && d.value) setData(d)
                else setData({ value: '50', value_classification: 'Neutral' })
            })
            .catch(e => {
                console.error('F&G Error:', e)
                setData({ value: '50', value_classification: 'Neutral' })
            })
    }, [])

    const val = parseInt(data?.value || '50')

    let color = '#fbbf24'
    if (val <= 25) color = '#ef5350'
    else if (val <= 45) color = '#f59e0b'
    else if (val >= 75) color = '#22c55e'
    else if (val >= 55) color = '#84cc16'

    return (
        <div className={styles.fearGreedWidget}>
            <div className={styles.fearGreedHeader}>
                <span className={styles.fearGreedTitle}>Crypto Fear & Greed</span>
            </div>

            <div className={styles.fearGreedGauge}>
                <div className={styles.fearGreedScore} style={{ color }}>{val}</div>
                <div className={styles.fearGreedLabel}>{data.value_classification}</div>
            </div>

            <div className={styles.barBackground}>
                <div
                    className={styles.longBar}
                    style={{ width: `${val}%`, background: color, boxShadow: `0 0 15px ${color}66` }}
                />
            </div>
            <div className={styles.fearGreedScale}>
                <span>Fear</span>
                <span>Neutral</span>
                <span>Greed</span>
            </div>
        </div>
    )
}

// 3. Event Calendar
export function EventCalendar() {
    const [events, setEvents] = useState([])

    useEffect(() => {
        fetch(API.EVENTS)
            .then(res => res.json())
            .then(data => {
                if (Array.isArray(data)) setEvents(data);
                else setEvents([]);
            })
            .catch(() => setEvents([]))
    }, [])

    if (events.length === 0) return null

    return (
        <div className={styles.calendarContainer}>
            <h3 className={styles.calendarTitle}>
                <span className={styles.icon}>📅</span> 주요 경제 일정
            </h3>
            <div className={styles.calendarList}>
                {(Array.isArray(events) ? events : []).map((ev, i) => {
                    if (!ev) return null;
                    const impactClass = ev.impact ? (styles[ev.impact] || '') : '';
                    return (
                        <div key={i} className={`${styles.calendarItem} ${impactClass}`}>
                            <div className={styles.dDay}>{ev.d_day || 'D-?'}</div>
                            <div className={styles.eventInfo}>
                                <div className={styles.eventTitle}>{ev.title || '일정 정보 없음'}</div>
                                <div className={styles.eventDate}>{ev.date || ''}</div>
                            </div>
                            <div className={styles.impactBadge}>{ev.impact || 'Normal'}</div>
                        </div>
                    );
                })}
            </div>
        </div>
    )
}

// 4. Daily Briefing
// 4. Daily Briefing (already here, keeping for context)
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
        <div className={styles.briefingContainer}>
            <div className={styles.briefingHeader}>
                ✨ 내일의 휴식을 위한 오늘의 체크포인트
            </div>
            <ul className={styles.briefingList}>
                {briefs.map((text, i) => (
                    <li key={i} className={styles.briefingItem}>
                        <span className={styles.briefingBullet}>•</span>
                        {text}
                    </li>
                ))}
            </ul>
        </div>
    )
}

// 5. Oasis Summary
export function OasisSummary() {
    const [summary, setSummary] = useState("시장의 흐름을 분석하고 있습니다. 잠시만 기다려주세요...")

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                const res = await fetch(API.STRATEGY)
                const data = await res.json()

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
        <div className={styles.oasisWrapper}>
            <div className={styles.oasisBadge}>OASIS BRIEF</div>
            <div className={styles.oasisMessage}>{summary}</div>
        </div>
    )
}

// 6. Big Whale Monitor
export function BigWhaleMonitor() {
    const [msgs, setMsgs] = useState([]);
    const [status, setStatus] = useState('Wait');

    useEffect(() => {
        let active = true;
        let ws = null;

        const connect = () => {
            try {
                ws = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@trade');
                ws.onopen = () => { if (active) setStatus('ON'); };
                ws.onmessage = (e) => {
                    if (!active) return;
                    try {
                        const m = JSON.parse(e.data);
                        const amount = parseFloat(m.p) * parseFloat(m.q);
                        if (amount >= 50000) {
                            const alert = {
                                side: m.m ? "SELL" : "BUY",
                                amount: amount,
                                timestamp: new Date(m.T).toTimeString().slice(0, 8)
                            };
                            setMsgs(p => [alert, ...p].slice(0, 15));
                        }
                    } catch (err) { }
                };
                ws.onerror = () => { if (active) setStatus('OFF'); };
                ws.onclose = () => { if (active) setTimeout(connect, 5000); };
            } catch (e) { }
        };

        connect();
        return () => { active = false; if (ws) ws.close(); };
    }, []);

    return (
        <div className={styles.whaleContainer}>
            <div className={styles.whaleHeader}>
                <span className={styles.whaleTitle}>🐋 실시간 고래 감시</span>
                <span className={`${styles.whaleStatusBadge} ${status === 'ON' ? styles.statusOn : styles.statusOff}`}>
                    ● {status}
                </span>
            </div>
            <div className={styles.whaleList}>
                {msgs.length === 0 ? (
                    <div className={styles.whalePlaceholder}>데이터 대기 중...</div>
                ) : (
                    msgs.map((m, i) => (
                        <div key={i} className={styles.whaleRow}>
                            <span className={m.side === 'BUY' ? styles.whaleBuy : styles.whaleSell}>
                                {m.side} {(m.amount / 1000).toFixed(0)}K
                            </span>
                            <span className={styles.whaleTime}>{m.timestamp}</span>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
