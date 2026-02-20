import { useState, useEffect, useRef } from 'react'
import styles from './ChatPanel.module.css'
import { API } from '../config'

const SEND_URL = API.CHAT_SEND

export function ChatPanel() {
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [myId] = useState('개미 ' + Math.floor(Math.random() * 1000))
    const messagesEndRef = useRef(null)

    // SSE 실시간 연결 (서버 부하 감소, 반응 속도 향상)
    useEffect(() => {
        // 1. 초기 데이터 로딩 (최근 50개)
        fetch(API.CHAT_MESSAGES)
            .then(res => res.json())
            .then(data => setMessages(data))
            .catch(err => console.error("Initial Load Error:", err))

        // 2. 실시간 스트림 연결
        const eventSource = new EventSource(API.CHAT_STREAM)

        eventSource.onmessage = (e) => {
            try {
                const newMsg = JSON.parse(e.data)
                setMessages(prev => [...prev.slice(-49), newMsg]) // 최신 50개 유지
            } catch (err) {
                // ping 메시지 등은 무시
            }
        }

        eventSource.onerror = (e) => {
            eventSource.close() // 에러 시 닫고 재연결 시도 (React가 리렌더링하며 재연결됨)
        }

        return () => {
            eventSource.close()
        }
    }, [])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const sendMessage = async (e) => {
        e.preventDefault()
        if (!input.trim()) return

        const msg = {
            sender: myId,
            text: input.trim(),
            timestamp: new Date().toLocaleTimeString().slice(0, 5)
        }

        try {
            await fetch(SEND_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(msg)
            })
            setInput('')
            // SSE가 자동으로 업데이트하므로 수동 fetch 불필요
        } catch (err) {
            console.error("Send failed:", err)
        }
    }

    return (
        <div className={styles.panel}>
            <div className={styles.header}>
                🔥 실시간 토론방
                <span className={styles.onlineBadge}>LIVE</span>
            </div>

            <div className={styles.messages}>
                {messages.map((msg, i) => (
                    <div key={i} className={`${styles.messageRow} ${msg.sender === myId ? styles.myMessage : ''}`}>
                        <div className={styles.sender}>{msg.sender}</div>
                        <div className={styles.bubble}>
                            {msg.text}
                            <span className={styles.time}>{msg.timestamp}</span>
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={sendMessage} className={styles.inputForm}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="매매 의견을 나눠보세요..."
                    className={styles.input}
                />
                <button type="submit" className={styles.sendBtn}>전송</button>
            </form>
        </div>
    )
}
