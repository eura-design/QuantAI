import { useState, useEffect } from 'react'
import styles from './NewsTicker.module.css'
import { API } from '../config'

export function NewsTicker() {
    const [news, setNews] = useState([])

    useEffect(() => {
        const fetchNews = () => {
            fetch(API.NEWS)
                .then(res => res.json())
                .then(data => setNews(data))
                .catch(() => { })
        }
        fetchNews()
        const timer = setInterval(fetchNews, 60000) // 1분마다 갱신
        return () => clearInterval(timer)
    }, [])

    if (news.length === 0) return null

    return (
        <div className={styles.tickerContainer}>
            <div className={styles.label}>LATEST NEWS</div>
            <div className={styles.track}>
                <div className={styles.content}>
                    {news.concat(news).map((item, i) => (
                        <span key={i} className={styles.newsItem}>
                            <span className={styles.dot}>•</span>
                            {item}
                        </span>
                    ))}
                </div>
            </div>
        </div>
    )
}
