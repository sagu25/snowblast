import { useState, useRef, useEffect } from 'react'
import { askChat, ApiError } from '../api.js'

const QUICK = [
  { q: "Who's affected?", key: 'who' },
  { q: 'Confidence?', key: 'confidence' },
  { q: 'False positives?', key: 'false' },
]

export default function ChatPanel({ incidentNumber, onClose }) {
  const [messages, setMessages] = useState([
    { text: `Assessment ready for ${incidentNumber}. Ask me anything about it.`, from: 'agent' },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const msgsRef = useRef(null)

  useEffect(() => {
    if (msgsRef.current) msgsRef.current.scrollTop = msgsRef.current.scrollHeight
  }, [messages])

  async function send(question) {
    if (!question.trim() || sending) return
    setMessages((m) => [...m, { text: question, from: 'user' }])
    setInput('')
    setSending(true)
    try {
      const { answer } = await askChat(incidentNumber, question)
      setMessages((m) => [...m, { text: answer, from: 'agent' }])
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Something went wrong asking that.'
      setMessages((m) => [...m, { text: msg, from: 'agent', error: true }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-head">
        Ask Blast Radius
        <button onClick={onClose}>×</button>
      </div>
      <div className="chat-msgs" ref={msgsRef}>
        {messages.map((m, i) => (
          <div className={'chat-msg' + (m.from === 'user' ? ' user' : '') + (m.error ? ' error' : '')} key={i}>
            {m.text}
          </div>
        ))}
      </div>
      <div className="chat-quick">
        {QUICK.map((q) => (
          <button key={q.key} onClick={() => send(q.q)}>{q.q}</button>
        ))}
      </div>
      <div className="chat-input">
        <input
          placeholder="Ask about this assessment…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send(input)}
        />
        <button onClick={() => send(input)}>Send</button>
      </div>
    </div>
  )
}
