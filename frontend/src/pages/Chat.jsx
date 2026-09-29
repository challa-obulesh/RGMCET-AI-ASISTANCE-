import ChatWindow from '../components/ChatWindow.jsx'

export default function Chat({ resetKey, activeConversationId, onNewConversation }) {
  return <ChatWindow resetKey={resetKey} activeConversationId={activeConversationId} onNewConversation={onNewConversation} />
}