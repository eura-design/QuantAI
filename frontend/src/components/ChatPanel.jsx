import { useState, useEffect, useRef } from 'react'
import styles from './ChatPanel.module.css'

const WS_URL = import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace('http', 'ws').replace('/api/strategy', '/ws/chat')
    : 'ws://localhost:8001/ws/chat'

export function ChatPanel() {
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [ws, setWs] = useState(null)
    const [myId] = useState('개미 ' + Math.floor(Math.random() * 1000))
    const messagesEndRef = useRef(null)

    useEffect(() => {
        const socket = new WebSocket(WS_URL)

        socket.onopen = () => {
            console.log('Chat Connected')
        }

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data)
            setMessages(prev => [...prev, data])
        }

        socket.onclose = () => {
            console.log('Chat Disconnected')
        }

        setWs(socket)

        return () => {
            socket.close()
        }
    }, [])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const sendMessage = (e) => {
        e.preventDefault()
        if (!input.trim() || !ws) return

        const msg = {
            sender: myId,
            text: input.trim(),
            timestamp: new Date().toLocaleTimeString().slice(0, 5)
        }

        ws.send(JSON.stringify(msg))
        setInput('')
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
