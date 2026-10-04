import { Bot, CalendarClock, GraduationCap, LayoutDashboard, LogIn, LogOut, MessageSquare, Plus, Sparkles, Users } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext.jsx'

export default function Sidebar({ page, onNavigate, onNewChat, onSelectChat, recentChats }) {
  const { user, logout } = useAuth()

  function handleLogout() {
    logout()
    onNavigate('login')
  }

  return (
    <nav className="sidebar" aria-label="Main navigation">
      <button className="brand" onClick={onNewChat} aria-label="RGMCET AI Campus Assistant — new chat">
        <div className="brand-mark"><Bot size={20} /></div>
        <div>
          <strong>RGMCET AI</strong>
          <small>Campus Assistant</small>
        </div>
      </button>

      <button className="new-chat" id="new-chat-button" onClick={onNewChat}>
        <Plus size={16} /> New conversation
      </button>

      <div className="primary-nav">
        <button id="nav-chat" className={`nav-item ${page === 'chat' ? 'active' : ''}`} onClick={() => onNavigate('chat')}>
          <MessageSquare size={17} /> Chat
        </button>
        <button id="nav-professors" className={`nav-item ${page === 'professors' ? 'active' : ''}`} onClick={() => onNavigate('professors')}>
          <Users size={17} /> Professors
        </button>
        {/* Show dashboards only when logged in */}
        {user?.role === 'student' && (
          <button id="nav-student" className={`nav-item ${page === 'student' ? 'active' : ''}`} onClick={() => onNavigate('student')}>
            <LayoutDashboard size={17} /> My Appointments
          </button>
        )}
        {user?.role === 'professor' && (
          <button id="nav-professor" className={`nav-item ${page === 'professor' ? 'active' : ''}`} onClick={() => onNavigate('professor')}>
            <CalendarClock size={17} /> Dashboard
          </button>
        )}
        {user?.role === 'admin' && (
          <button id="nav-admin" className={`nav-item ${page === 'admin' ? 'active' : ''}`} onClick={() => onNavigate('admin')}>
            <LayoutDashboard size={17} /> Admin Panel
          </button>
        )}
        <button id="nav-appointments" className={`nav-item ${page === 'appointments' ? 'active' : ''}`} onClick={() => onNavigate('appointments')}>
          <CalendarClock size={17} /> Appointments
        </button>
      </div>

      {recentChats?.length > 0 && (
        <div className="recent-section">
          <p className="section-label">RECENT CHATS</p>
          {recentChats.map((chat) => (
            <button key={chat.id} className="recent-chat" onClick={() => onSelectChat(chat.id)}>
              <MessageSquare size={13} />
              <span>{chat.title}</span>
            </button>
          ))}
        </div>
      )}

      <div className="sidebar-bottom">
        {user ? (
          <>
            <div className="status-dot" />
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user.name}
            </span>
            <span className="demo-label" style={{ background: user.role === 'professor' ? '#c8e6f8' : undefined, color: user.role === 'professor' ? '#1a5f8a' : undefined }}>
              {user.role.toUpperCase()}
            </span>
            <button id="logout-button" className="icon-button" onClick={handleLogout} aria-label="Sign out" title="Sign out" style={{ marginLeft: 4 }}>
              <LogOut size={14} />
            </button>
          </>
        ) : (
          <>
            <Sparkles size={13} />
            <span style={{ flex: 1 }}>Demo mode</span>
            <button id="nav-login" className="demo-label" style={{ cursor: 'pointer', border: 'none', background: '#e8f1d3', color: '#163d31' }} onClick={() => onNavigate('login')}>
              Sign in
            </button>
          </>
        )}
      </div>
    </nav>
  )
}