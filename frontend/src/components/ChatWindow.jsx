import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Bot, CircleHelp, GraduationCap, LibraryBig, Users, ShieldCheck, Sparkles, Building2 } from 'lucide-react'
import { api, DEMO_STUDENT_ID } from '../services/api.js'
import { useAuth } from '../contexts/AuthContext.jsx'

const suggestions = [
  { text: 'What is CSE Data Science?', icon: GraduationCap },
  { text: 'Who is the HOD of CSE Data Science?', icon: Users },
  { text: 'What facilities are available on campus?', icon: Building2 },
  { text: 'Does RGMCET have a library?', icon: LibraryBig },
  { text: 'Tell me about RGMCET.', icon: Sparkles },
  { text: 'Ravi sir schedule enti?', icon: Users },
]

export default function ChatWindow({ resetKey, activeConversationId, onNewConversation }) {
  const [messages, setMessages] = useState([])
  const [value, setValue] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  const { user } = useAuth()

  useEffect(() => {
    setValue(''); setError('')
    if (activeConversationId) {
      if (user && user.role === 'student') {
        setBusy(true)
        api.get(`/api/chat/sessions/${activeConversationId}`)
          .then(session => {
            const mappedMessages = session.turns.flatMap(turn => [
              { role: 'user', text: turn.user_message },
              { role: 'assistant', text: turn.assistant_message, intent: turn.intent, language: turn.language }
            ])
            setMessages(mappedMessages)
            setSessionId(activeConversationId)
            setBusy(false)
          })
          .catch(err => {
            console.error("Failed to load chat session", err)
            try {
              const saved = JSON.parse(localStorage.getItem(`rgmcet-chat-${activeConversationId}`) || 'null')
              setMessages(saved?.messages || [])
              setSessionId(activeConversationId)
            } catch {
              setMessages([]); setSessionId(activeConversationId)
            }
            setBusy(false)
          })
      } else {
        try {
          const saved = JSON.parse(localStorage.getItem(`rgmcet-chat-${activeConversationId}`) || 'null')
          setMessages(saved?.messages || [])
          setSessionId(activeConversationId)
        } catch {
          setMessages([]); setSessionId(activeConversationId)
        }
      }
    } else {
      setMessages([]); setSessionId(null)
    }
  }, [resetKey, activeConversationId, user])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])
  useEffect(() => {
    if (!sessionId || !messages.length) return
    try {
      const previous = JSON.parse(localStorage.getItem(`rgmcet-chat-${sessionId}`) || '{}')
      localStorage.setItem(`rgmcet-chat-${sessionId}`, JSON.stringify({
        title: previous.title || messages.find((item) => item.role === 'user')?.text?.slice(0, 44) || 'New conversation',
        messages,
      }))
    } catch { /* Storage can be unavailable in private browsing. */ }
  }, [messages, sessionId])

  async function send(text = value) {
    const clean = text.trim()
    if (!clean || busy) return
    const conversationId = sessionId || `web-${crypto.randomUUID()}`
    setMessages((items) => [...items, { role: 'user', text: clean }])
    setSessionId(conversationId)
    setValue(''); setError(''); setBusy(true)
    if (messages.length === 0) onNewConversation(conversationId, clean)
    try {
      const result = await api.chat({ message: clean, session_id: conversationId, student_id: (user && user.role === 'student' && user.user_id) ? user.user_id : DEMO_STUDENT_ID })
      setSessionId(result.session_id)
      setMessages((items) => [...items, {
        role: 'assistant',
        text: result.message,
        verified: result.verified,
        sources: result.sources || [],
        intent: result.intent,
        language: result.language,
      }])
    } catch (exception) {
      setError(exception.message)
      setMessages((items) => [...items, { role: 'assistant', text: 'I could not reach the campus assistant just now. Please try again.' }])
    } finally {
      setBusy(false); inputRef.current?.focus()
    }
  }

  return (
    <section className="chat-view" aria-label="Campus assistant chat">
      {messages.length === 0 ? (
        <div className="welcome-block">
          <div className="welcome-symbol"><Bot size={25} /></div>
          <p className="eyebrow">RGMCET AI CAMPUS ASSISTANT — LLM + VERIFIED OFFICIAL KNOWLEDGE</p>
          <h1>What would you like<br />to know today?</h1>
          <p className="welcome-copy">Ask about RGMCET departments, faculty, facilities, professors and appointments. Answers are grounded in verified official RGMCET data.</p>
          <div className="suggestion-grid">
            {suggestions.map(({ text, icon: Icon }) => (
              <button key={text} className="suggestion" onClick={() => send(text)} disabled={busy}>
                <Icon size={17} /><span>{text}</span><ArrowUp size={15} className="suggestion-arrow" />
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="message-list">
          {messages.map((message, index) => (
            <article className={`message-row ${message.role}`} key={`${message.role}-${index}`}>
              {message.role === 'assistant' && <span className="message-avatar"><Bot size={16} /></span>}
              <div className="message-content">
                <div className="message-meta">
                  <span className="message-author">{message.role === 'user' ? 'You' : 'RGMCET AI'}</span>
                  {message.role === 'assistant' && message.verified && (
                    <span className="verified-badge" title="Answer grounded in verified RGMCET official data">
                      <ShieldCheck size={11} /> Verified
                    </span>
                  )}
                  {message.role === 'assistant' && message.intent && message.intent !== 'UNKNOWN' && (
                    <span className="intent-badge">{message.intent.replace(/_/g, '\u00a0')}</span>
                  )}
                </div>
                <p>{message.text}</p>
                {message.verified && message.sources?.length > 0 && <div className="message-sources">
                  <strong><ShieldCheck size={11} /> Verified Sources:</strong>
                  <ul>
                    {message.sources.map((source) => (
                      <li key={source.url}>
                        <div><strong>Source:</strong> <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a></div>
                        {source.department && source.department !== 'General' && <div><strong>Department:</strong> {source.department}</div>}
                        {source.last_checked && source.last_checked !== 'N/A' && <div><strong>Last checked:</strong> {new Date(source.last_checked).toLocaleDateString()}</div>}
                      </li>
                    ))}
                  </ul>
                </div>}
              </div>
            </article>
          ))}
          {busy && <div className="thinking"><span /><span /><span /> <small>Searching RGMCET knowledge...</small></div>}
          <div ref={bottomRef} />
        </div>
      )}
      <div className="composer-wrap">
        {error && <div className="inline-error"><CircleHelp size={15} /> {error}</div>}
        <form className="composer" onSubmit={(event) => { event.preventDefault(); send() }}>
          <textarea ref={inputRef} rows="1" value={value} placeholder="Ask RGMCET AI... (English, Telugu, or Roman Telugu)" aria-label="Message RGMCET AI" disabled={busy}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send() } }} />
          <button className="send-button" type="submit" disabled={busy || !value.trim()} aria-label="Send message"><ArrowUp size={19} /></button>
        </form>
        <p className="composer-note">Answers are grounded in verified RGMCET official data. LLM is used only for natural language generation.</p>
      </div>
    </section>
  )
}