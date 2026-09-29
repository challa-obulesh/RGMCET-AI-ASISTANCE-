import { useState } from 'react'
import { Menu, PanelLeftClose, Sparkles } from 'lucide-react'
import Sidebar from './components/Sidebar.jsx'
import Chat from './pages/Chat.jsx'
import Professors from './pages/Professors.jsx'
import Appointments from './pages/Appointments.jsx'

const pageTitles = { chat: 'New conversation', professors: 'Professor directory', appointments: 'Appointments' }

export default function App() {
  const [page, setPage] = useState('chat')
  const [resetKey, setResetKey] = useState(0)
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [recentChats, setRecentChats] = useState(() => {
    try { return JSON.parse(localStorage.getItem('rgmcet-recent-chats') || '[]') } catch { return [] }
  })
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [desktopCollapsed, setDesktopCollapsed] = useState(false)
  function newChat() { setPage('chat'); setActiveConversationId(null); setResetKey((key) => key + 1); setSidebarOpen(false) }
  function navigate(next) { setPage(next); setSidebarOpen(false) }
  function addRecent(id, title) {
    setRecentChats((items) => {
      const updated = [{ id, title: title.slice(0, 44) }, ...items.filter((item) => item.id !== id)].slice(0, 8)
      localStorage.setItem('rgmcet-recent-chats', JSON.stringify(updated))
      return updated
    })
  }
  function selectChat(id) { setPage('chat'); setActiveConversationId(id); setResetKey((key) => key + 1); setSidebarOpen(false) }
  return <div className="app-shell">
    <div className={`sidebar-overlay ${sidebarOpen ? 'visible' : ''}`} onClick={() => setSidebarOpen(false)} />
    <div className={`sidebar-drawer ${sidebarOpen ? 'open' : ''} ${desktopCollapsed ? 'collapsed' : ''}`}><Sidebar page={page} onNavigate={navigate} onNewChat={newChat} onSelectChat={selectChat} recentChats={recentChats} /></div>
    <div className="workspace">
      <header className="topbar">
        <div className="topbar-start"><button className="icon-button mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={20} /></button><button className="icon-button desktop-collapse" onClick={() => setDesktopCollapsed((collapsed) => !collapsed)} aria-label="Toggle navigation"><PanelLeftClose size={18} /></button><span className="topbar-divider" /><span className="topbar-title">{pageTitles[page]}</span></div>
        <div className="topbar-tag"><Sparkles size={14} /> CAMPUS ASSISTANT</div>
      </header>
      <main className={`main-view ${page === 'chat' ? 'chat-main' : ''}`}>
        {page === 'chat' && <Chat key={resetKey} resetKey={resetKey} activeConversationId={activeConversationId} onNewConversation={addRecent} />}
        {page === 'professors' && <Professors />}
        {page === 'appointments' && <Appointments />}
      </main>
    </div>
  </div>
}