import { useEffect, useState } from 'react'
import { Menu, PanelLeftClose, Sparkles } from 'lucide-react'
import { AuthProvider, useAuth } from './contexts/AuthContext.jsx'
import { api } from './services/api.js'
import Sidebar from './components/Sidebar.jsx'
import Chat from './pages/Chat.jsx'
import Professors from './pages/Professors.jsx'
import Appointments from './pages/Appointments.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import StudentDashboard from './pages/StudentDashboard.jsx'
import ProfessorDashboard from './pages/ProfessorDashboard.jsx'
import AdminDashboard from './pages/AdminDashboard.jsx'

const pageTitles = {
  chat: 'New conversation',
  professors: 'Professor directory',
  appointments: 'Appointments',
  student: 'My Appointments',
  professor: 'Professor Dashboard',
  admin: 'Admin Dashboard',
  login: 'Sign in',
  register: 'Create account',
}

// Pages that don't show the sidebar / topbar (full-screen auth pages)
const AUTH_PAGES = new Set(['login', 'register'])
// Pages that require authentication
const PROTECTED_PAGES = new Set(['student', 'professor', 'admin'])

function AppShell() {
  const { user, loading } = useAuth()
  const [page, setPage] = useState('chat')
  const [resetKey, setResetKey] = useState(0)
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [recentChats, setRecentChats] = useState(() => {
    try { return JSON.parse(localStorage.getItem('rgmcet-recent-chats') || '[]') } catch { return [] }
  })
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [desktopCollapsed, setDesktopCollapsed] = useState(false)

  function newChat() { setPage('chat'); setActiveConversationId(null); setResetKey((k) => k + 1); setSidebarOpen(false) }

  function navigate(next) {
    // Guard protected pages — redirect to login
    if (PROTECTED_PAGES.has(next) && !user) {
      setPage('login')
    } else {
      setPage(next)
    }
    setSidebarOpen(false)
  }

  useEffect(() => {
    if (loading) return
    if (user && (page === 'login' || page === 'register')) {
      setPage(user.role === 'professor' ? 'professor' : 'chat')
    }
    if (!user && PROTECTED_PAGES.has(page)) {
      setPage('login')
    }

    if (user && user.role === 'student') {
      api.get('/chat/sessions').then(sessions => {
        if (Array.isArray(sessions) && sessions.length > 0) {
          setRecentChats(sessions.map(s => ({
            id: s.session_id,
            title: s.turns[0]?.user_message?.slice(0, 44) || 'Conversation'
          })))
        }
      }).catch(err => console.error("Failed to load chat sessions", err))
    }
  }, [user, loading, page])

  function addRecent(id, title) {
    setRecentChats((items) => {
      const updated = [{ id, title: title.slice(0, 44) }, ...items.filter((item) => item.id !== id)].slice(0, 8)
      if (!user) {
        localStorage.setItem('rgmcet-recent-chats', JSON.stringify(updated))
      }
      return updated
    })
  }

  function selectChat(id) { setPage('chat'); setActiveConversationId(id); setResetKey((k) => k + 1); setSidebarOpen(false) }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fbfcf8' }}>
        <div className="thinking"><span /><span /><span /><small>Loading RGMCET AI…</small></div>
      </div>
    )
  }

  // Full-screen auth pages
  if (AUTH_PAGES.has(page)) {
    if (page === 'login') return <Login onNavigate={navigate} />
    if (page === 'register') return <Register onNavigate={navigate} />
  }

  return (
    <div className="app-shell">
      <div className={`sidebar-overlay ${sidebarOpen ? 'visible' : ''}`} onClick={() => setSidebarOpen(false)} />
      <div className={`sidebar-drawer ${sidebarOpen ? 'open' : ''} ${desktopCollapsed ? 'collapsed' : ''}`}>
        <Sidebar
          page={page}
          onNavigate={navigate}
          onNewChat={newChat}
          onSelectChat={selectChat}
          recentChats={recentChats}
        />
      </div>
      <div className="workspace">
        <header className="topbar">
          <div className="topbar-start">
            <button className="icon-button mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
            <button className="icon-button desktop-collapse" onClick={() => setDesktopCollapsed((c) => !c)} aria-label="Toggle navigation"><PanelLeftClose size={18} /></button>
            <span className="topbar-divider" />
            <span className="topbar-title">{pageTitles[page] || page}</span>
          </div>
          <div className="topbar-tag"><Sparkles size={14} /> CAMPUS ASSISTANT</div>
        </header>
        <main className={`main-view ${page === 'chat' ? 'chat-main' : ''}`}>
          {page === 'chat' && <Chat key={resetKey} resetKey={resetKey} activeConversationId={activeConversationId} onNewConversation={addRecent} />}
          {page === 'professors' && <Professors />}
          {page === 'appointments' && <Appointments />}
          {page === 'student' && (user ? <StudentDashboard /> : null)}
          {page === 'professor' && (user?.role === 'professor' ? <ProfessorDashboard /> : null)}
          {page === 'admin' && (user?.role === 'admin' ? <AdminDashboard /> : null)}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  )
}