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
        // 실시간 스트림 연결 (개선된 백엔드는 첫 연결 시 최근 메시지 50개를 함께 보냄)
        const eventSource = new EventSource(API.CHAT_STREAM)

        eventSource.onmessage = (e) => {
            try {
                const newMsg = JSON.parse(e.data)
                setMessages(prev => {
                    // 중복 방지 로직 (ID가 있다면 더 좋겠지만, 여기선 텍스트와 시간으로 간단히 체크)
                    const isDuplicate = prev.some(m => m.text === newMsg.text && m.timestamp === newMsg.timestamp && m.sender === newMsg.sender)
                    if (isDuplicate) return prev
                    return [...prev.slice(-49), newMsg]
                })
            } catch (err) {
                console.error("Parse Error:", err)
            }
        }

        eventSource.onerror = (e) => {
            console.error("SSE Connection Error:", e)
            eventSource.close()
        }

        return () => eventSource.close()
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

        // [낙관적 업데이트] 서버 응답 기다리지 않고 즉시 화면에 표시
        setMessages(prev => [...prev.slice(-49), msg])
        setInput('')

        try {
            await fetch(SEND_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(msg)
            })
            // 전송 성공! (이미 화면에 표시했으므로 추가 작업 없음)
        } catch (err) {
            console.error("Send failed:", err)
            // 전송 실패 시 에러 표시 혹은 롤백 (여기선 생략)
            alert("메시지 전송 실패. 네트워크를 확인하세요.")
        }
    }

    return (
        <div className={styles.panel}>
            <div className={styles.header}>
                🔥 실시간 토론방
                <span className={styles.onlineBadge}>LIVE</span>
            </div>

            <div className={styles.messages}>
                {(Array.isArray(messages) ? messages : []).map((msg, i) => {
                    if (!msg) return null;
                    return (
                        <div key={i} className={`${styles.messageRow} ${msg.sender === myId ? styles.myMessage : ''}`}>
                            <div className={styles.sender}>{msg.sender || 'Anonymous'}</div>
                            <div className={styles.bubble}>
                                {msg.text || ''}
                                <span className={styles.time}>{msg.timestamp || ''}</span>
                            </div>
                        </div>
                    );
                })}
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
