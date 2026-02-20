import { useState, useEffect } from 'react'
import styles from './FearGreed.module.css'
import { API } from '../config'

const API_URL = API.FEAR_GREED

export function FearGreed() {
    const [data, setData] = useState({ value: '50', value_classification: 'Neutral' })

    useEffect(() => {
        fetch(API_URL)
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

    // 색상 결정
    let color = '#fbbf24' // Neutral
    if (val <= 25) color = '#ef5350' // Ex. Fear
    else if (val <= 45) color = '#f59e0b' // Fear
    else if (val >= 75) color = '#22c55e' // Ex. Greed
    else if (val >= 55) color = '#84cc16' // Greed

    return (
        <div className={styles.widget}>
            <div className={styles.header}>
                <span className={styles.title}>Crypto Fear & Greed</span>
                <span className={styles.refresh} onClick={() => location.reload()}>↻</span>
            </div>

            <div className={styles.gaugeContainer}>
                <div className={styles.score} style={{ color }}>{val}</div>
                <div className={styles.label}>{data.value_classification}</div>
            </div>

            <div className={styles.barBg}>
                <div
                    className={styles.barFill}
                    style={{ width: `${val}%`, background: color }}
                />
            </div>
            <div className={styles.scale}>
                <span>Fear</span>
                <span>Neutral</span>
                <span>Greed</span>
            </div>
        </div>
    )
}
