import { BookOpen, CalendarDays, MessageSquare, Plus, Users } from 'lucide-react'

const destinations = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'professors', label: 'Professors', icon: Users },
  { id: 'appointments', label: 'My appointments', icon: CalendarDays },
]

export default function Sidebar({ page, onNavigate, onNewChat, onSelectChat, recentChats = [] }) {
  return (
    <aside className="sidebar">
      <button className="brand" onClick={() => onNavigate('chat')} aria-label="RGMCET AI home">
        <span className="brand-mark"><BookOpen size={19} strokeWidth={2.2} /></span>
        <span><strong>RGMCET</strong><small>AI CAMPUS ASSISTANT</small></span>
      </button>
      <button className="new-chat" onClick={onNewChat}><Plus size={17} /> New chat</button>
      <nav className="primary-nav" aria-label="Primary navigation">
        {destinations.map(({ id, label, icon: Icon }) => (
          <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => onNavigate(id)}>
            <Icon size={17} /> {label}
          </button>
        ))}
      </nav>
      <div className="recent-section">
        <p className="section-label">RECENT CHATS</p>
        {recentChats.length ? recentChats.map((chat) => (
          <button className="recent-chat" key={chat.id} onClick={() => onSelectChat(chat.id)} title={chat.title}>
            <MessageSquare size={14} /><span>{chat.title}</span>
          </button>
        )) : <span className="recent-empty">Your conversations will appear here</span>}
      </div>
      <div className="sidebar-bottom"><span className="status-dot" /> Web MVP <span className="demo-label">DEMO</span></div>
    </aside>
  )
}