import { useState, useEffect, useRef } from 'react'
import styles from './ChatPanel.module.css'
import { useLanguage } from '../contexts/LanguageContext'

export function ChatPanel() {
    const { t, lang } = useLanguage()
    const [messages, setMessages] = useState([
        { id: 1, user: 'AI_ANALYST', text: 'Monitoring structural support at 97,400. Strength is increasing.', isAI: true, time: '12:00' },
        { id: 2, user: `${t('chat.traderPrefix')}_77`, text: '드디어 반등 하나요? 롱 타점 보고 있습니다.', isAI: false, time: '12:05' },
    ])
    const [input, setInput] = useState('')
    const chatEndRef = useRef(null)

    const scrollToBottom = () => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => { scrollToBottom() }, [messages])

    const handleSend = (e) => {
        e.preventDefault()
        if (!input.trim()) return
        const newMsg = {
            id: Date.now(),
            user: `${t('chat.traderPrefix')}_09`,
            text: input,
            isAI: false,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
        setMessages([...messages, newMsg])
        setInput('')
    }

    return (
        <div className={styles.panel}>
            <div className={styles.header}>
                <span>{t('chat.title')}</span>
                <span className={styles.onlineBadge}>{t('chat.online')}</span>
            </div>

            <div className={styles.messages}>
                {messages.map(m => (
                    <div key={m.id} className={`${styles.messageRow} ${m.user.startsWith(t('chat.traderPrefix')) ? styles.myMessage : ''}`}>
                        <span className={styles.sender}>{m.user}</span>
                        <div className={styles.bubble}>{m.text}</div>
                        <span className={styles.time}>{m.time}</span>
                    </div>
                ))}
                <div ref={chatEndRef} />
            </div>

            <form className={styles.inputForm} onSubmit={handleSend}>
                <input
                    type="text"
                    className={styles.input}
                    placeholder={t('chat.placeholder')}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                />
                <button type="submit" className={styles.sendBtn}>{t('chat.send')}</button>
            </form>
        </div>
    )
}
