import { useState, useEffect } from 'react'
import styles from './EventCalendar.module.css'
import { API } from '../config'

export function EventCalendar() {
    const [events, setEvents] = useState([])

    useEffect(() => {
        fetch(API.EVENTS)
            .then(res => res.json())
            .then(data => setEvents(data))
            .catch(() => { })
    }, [])

    if (events.length === 0) return null

    return (
        <div className={styles.container}>
            <h3 className={styles.title}>
                <span className={styles.icon}>📅</span> 주요 경제 일정
            </h3>
            <div className={styles.list}>
                {events.map((ev, i) => (
                    <div key={i} className={`${styles.item} ${styles[ev.impact]}`}>
                        <div className={styles.dDay}>{ev.d_day}</div>
                        <div className={styles.info}>
                            <div className={styles.eventTitle}>{ev.title}</div>
                            <div className={styles.date}>{ev.date}</div>
                        </div>
                        <div className={styles.impactBadge}>{ev.impact}</div>
                    </div>
                ))}
            </div>
        </div>
    )
}
