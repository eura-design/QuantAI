import { useState, useEffect, useRef } from 'react'
import styles from './ChatPanel.module.css'

// 하드코딩 (무조건 배포 주소 사용)
const WS_URL = 'wss://quantai-production.up.railway.app/ws/chat'

export function ChatPanel() {
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [myId] = useState('개미 ' + Math.floor(Math.random() * 1000))
    const [isConnected, setIsConnected] = useState(false)
    const [lastError, setLastError] = useState(null)
    const wsRef = useRef(null)
    const messagesEndRef = useRef(null)

    // 재연결 및 소켓 관리
    useEffect(() => {
        let reconnectTimer

        function connect() {
            if (wsRef.current?.readyState === WebSocket.OPEN) return

            const socket = new WebSocket(WS_URL)

            socket.onopen = () => {
                console.log('Chat Connected')
                setIsConnected(true)
                if (reconnectTimer) clearTimeout(reconnectTimer)
            }

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data)
                setMessages(prev => [...prev, data])
            }

            socket.onclose = () => {
                console.log('Chat Disconnected')
                setIsConnected(false)
                wsRef.current = null
                // 3초 후 재연결 시도
                reconnectTimer = setTimeout(connect, 3000)
            }

            socket.onerror = (err) => {
                console.log('Chat Error:', err)
                socket.close()
            }

            wsRef.current = socket
        }

        connect()

        return () => {
            if (wsRef.current) wsRef.current.close()
            if (reconnectTimer) clearTimeout(reconnectTimer)
        }
    }, [])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const sendMessage = (e) => {
        e.preventDefault()
        if (!input.trim() || !isConnected || !wsRef.current) return

        const msg = {
            sender: myId,
            text: input.trim(),
            timestamp: new Date().toLocaleTimeString().slice(0, 5)
        }

        try {
            wsRef.current.send(JSON.stringify(msg))
            setInput('')
        } catch (err) {
            console.error("Send failed:", err)
        }
    }

    return (
        <div className={styles.panel}>
            <div className={styles.header}>
                🔥 실시간 토론방
                <span className={styles.onlineBadge} style={{ background: isConnected ? '#ef5350' : '#64748b' }}>
                    {isConnected ? 'LIVE' : '연결 중...'}
                </span>
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

                {!isConnected && (
                    <div style={{ fontSize: '0.6rem', color: '#ef5350', padding: '10px', textAlign: 'center', background: 'rgba(239,83,80,0.1)', borderRadius: '4px', margin: '10px 0' }}>
                        <div>상태: {lastError || '연결 시도 중...'}</div>
                        <div style={{ marginTop: '4px', opacity: 0.7 }}>Target: {WS_URL}</div>
                    </div>
                )}

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
