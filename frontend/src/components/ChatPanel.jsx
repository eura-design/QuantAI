// 무조건 배포 주소 사용 (하드코딩)
const MSG_URL = 'https://quantai-production.up.railway.app/api/chat/messages'
const SEND_URL = 'https://quantai-production.up.railway.app/api/chat/send'

export function ChatPanel() {
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [myId] = useState('개미 ' + Math.floor(Math.random() * 1000))
    const messagesEndRef = useRef(null)

    // 1초마다 메시지 가져오기 (Polling)
    useEffect(() => {
        const fetchMessages = () => {
            fetch(MSG_URL)
                .then(r => r.json())
                .then(data => {
                    // 데이터가 배열인지 확인
                    if (Array.isArray(data)) {
                        setMessages(data)
                    }
                })
                .catch(e => console.error("Chat polling error:", e))
        }

        fetchMessages() // 즉시 실행
        const timer = setInterval(fetchMessages, 1000) // 1초 반복

        return () => clearInterval(timer)
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
            // 전송 직후 바로 리스트 갱신
            const r = await fetch(MSG_URL)
            const data = await r.json()
            if (Array.isArray(data)) setMessages(data)
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
