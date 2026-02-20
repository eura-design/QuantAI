import { useState, useEffect } from 'react'
import styles from './EventCalendar.module.css'
import { API } from '../config'

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
        <div className={styles.container}>
            <h3 className={styles.title}>
                <span className={styles.icon}>📅</span> 주요 경제 일정
            </h3>
            <div className={styles.list}>
                {(Array.isArray(events) ? events : []).map((ev, i) => {
                    if (!ev) return null;
                    const impactClass = ev.impact ? (styles[ev.impact] || '') : '';
                    return (
                        <div key={i} className={`${styles.item} ${impactClass}`}>
                            <div className={styles.dDay}>{ev.d_day || 'D-?'}</div>
                            <div className={styles.info}>
                                <div className={styles.eventTitle}>{ev.title || '일정 정보 없음'}</div>
                                <div className={styles.date}>{ev.date || ''}</div>
                            </div>
                            <div className={styles.impactBadge}>{ev.impact || 'Normal'}</div>
                        </div>
                    );
                })}
            </div>
        </div>
    )
}
