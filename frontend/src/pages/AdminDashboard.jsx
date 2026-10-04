import { useState, useEffect } from 'react'
import { api } from '../services/api'
import { CheckCircle, XCircle, AlertCircle, RefreshCw, Server, Users, MessageSquare, Database, FileText } from 'lucide-react'

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('overview')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchData()
  }, [])

  async function fetchData() {
    setLoading(true)
    setError(null)
    try {
      const overview = await api.get('/admin/overview')
      setData(overview)
    } catch (err) {
      setError(err.message || 'Failed to load admin overview')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="page-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>Loading Admin Data...</div>
  if (error) return <div className="page-container" style={{ color: 'red', display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>{error}</div>
  if (!data) return null

  return (
    <div className="page-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 24 }}>Admin Dashboard</h1>
        <button onClick={fetchData} className="action-button primary" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 24, borderBottom: '1px solid #eee', paddingBottom: 12 }}>
        {['overview', 'knowledge', 'system', 'audit'].map(tab => (
          <button 
            key={tab} 
            onClick={() => setActiveTab(tab)} 
            style={{ 
              background: 'none', border: 'none', cursor: 'pointer', 
              fontSize: 16, fontWeight: activeTab === tab ? 'bold' : 'normal',
              color: activeTab === tab ? '#163d31' : '#666'
            }}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, color: '#666' }}>
              <Users size={20} /> <span style={{ fontWeight: 600 }}>Total Users</span>
            </div>
            <div style={{ fontSize: 32, fontWeight: 'bold' }}>{data.users.total}</div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>{data.users.students} Students | {data.users.professors} Profs | {data.users.admins} Admins</div>
          </div>
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, color: '#666' }}>
              <FileText size={20} /> <span style={{ fontWeight: 600 }}>Knowledge Records</span>
            </div>
            <div style={{ fontSize: 32, fontWeight: 'bold' }}>{data.knowledge.total}</div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>{data.knowledge.verified} Verified | {data.knowledge.unverified} Unverified</div>
          </div>
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, color: '#666' }}>
              <MessageSquare size={20} /> <span style={{ fontWeight: 600 }}>Appointments</span>
            </div>
            <div style={{ fontSize: 32, fontWeight: 'bold' }}>{data.appointments.total}</div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>{data.appointments.pending} Pending | {data.appointments.completed} Completed</div>
          </div>
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12, color: '#666' }}>
              <Database size={20} /> <span style={{ fontWeight: 600 }}>System Health</span>
            </div>
            <div style={{ fontSize: 16, fontWeight: 'bold', display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>DB:</span> <span style={{ color: 'green' }}>{data.system.database}</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>LLM:</span> <span style={{ color: 'green' }}>{data.system.llm}</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>RAG:</span> <span style={{ color: 'green' }}>{data.system.rag}</span></div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'knowledge' && <AdminKnowledge />}
      {activeTab === 'system' && <AdminSystem />}
      {activeTab === 'audit' && <AdminAudit />}
    </div>
  )
}

function AdminSystem() {
  return <div>System advanced health and analytics coming soon.</div>
}

function AdminAudit() {
  const [logs, setLogs] = useState([])
  
  useEffect(() => {
    api.get('/admin/audit-logs').then(setLogs).catch(console.error)
  }, [])
  
  return (
    <div>
      <h3 style={{ marginTop: 0 }}>Audit Logs</h3>
      {logs.length === 0 ? <p>No audit logs found.</p> : (
        <div style={{ overflowX: 'auto', background: 'white', borderRadius: 8, border: '1px solid #eee' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: '#fbfcf8', borderBottom: '1px solid #eee' }}>
                <th style={{ padding: 12 }}>Time</th>
                <th style={{ padding: 12 }}>Admin</th>
                <th style={{ padding: 12 }}>Action</th>
                <th style={{ padding: 12 }}>Target</th>
                <th style={{ padding: 12 }}>Result</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #f5f5f5', fontSize: 14 }}>
                  <td style={{ padding: 12, color: '#666' }}>{new Date(log.timestamp).toLocaleString()}</td>
                  <td style={{ padding: 12 }}>{log.admin_email}</td>
                  <td style={{ padding: 12, fontWeight: 500 }}>{log.action}</td>
                  <td style={{ padding: 12 }}>{log.target_type} ({log.target_id})</td>
                  <td style={{ padding: 12, color: log.result === 'SUCCESS' ? 'green' : 'inherit' }}>{log.result}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function AdminKnowledge() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [reindexing, setReindexing] = useState(false)
  
  useEffect(() => {
    loadKnowledge()
  }, [])
  
  async function loadKnowledge() {
    setLoading(true)
    try {
      const data = await api.get('/admin/knowledge')
      setRecords(data)
    } catch (err) {
      alert('Failed to load knowledge')
    } finally {
      setLoading(false)
    }
  }
  
  async function handleVerify(id, currentVerified) {
    try {
      await api.post(`/admin/knowledge/${id}/${currentVerified ? 'unverify' : 'verify'}`)
      loadKnowledge()
    } catch (err) {
      alert('Action failed')
    }
  }
  
  async function handleDelete(id) {
    if (!confirm('Are you sure you want to delete this knowledge record?')) return
    try {
      await api.delete(`/admin/knowledge/${id}`)
      loadKnowledge()
    } catch (err) {
      alert('Delete failed')
    }
  }
  
  async function handleReindex() {
    setReindexing(true)
    try {
      const res = await api.post('/admin/knowledge/reindex')
      alert(`Reindex complete. Processed ${res.records_processed}, indexed ${res.records_indexed}.`)
      loadKnowledge()
    } catch (err) {
      alert('Reindex failed')
    } finally {
      setReindexing(false)
    }
  }
  
  if (loading) return <div>Loading records...</div>
  
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>Knowledge Records ({records.length})</h3>
        <button onClick={handleReindex} disabled={reindexing} className="action-button primary">
          {reindexing ? 'Indexing...' : 'Re-index Pending'}
        </button>
      </div>
      
      <div style={{ overflowX: 'auto', background: 'white', borderRadius: 8, border: '1px solid #eee' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: '#fbfcf8', borderBottom: '1px solid #eee' }}>
              <th style={{ padding: 12 }}>Title</th>
              <th style={{ padding: 12 }}>Kind / Dept</th>
              <th style={{ padding: 12 }}>Verified</th>
              <th style={{ padding: 12 }}>Status</th>
              <th style={{ padding: 12 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r, i) => {
              const id = r.id || r.source
              const rec = r.original_record || {}
              return (
                <tr key={i} style={{ borderBottom: '1px solid #f5f5f5', fontSize: 14 }}>
                  <td style={{ padding: 12, maxWidth: 300, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={rec.name || rec.title || r.content}>
                    {rec.name || rec.title || r.content?.slice(0, 30)}
                  </td>
                  <td style={{ padding: 12 }}>{r.kind} <br/><span style={{ fontSize: 11, color: '#666' }}>{rec.department || ''}</span></td>
                  <td style={{ padding: 12 }}>
                    {rec.verified ? <span style={{ color: 'green', display: 'flex', alignItems: 'center', gap: 4 }}><CheckCircle size={14}/> Yes</span> : <span style={{ color: 'orange', display: 'flex', alignItems: 'center', gap: 4 }}><AlertCircle size={14}/> No</span>}
                  </td>
                  <td style={{ padding: 12 }}>
                    {r.index_status === 'INDEX_PENDING' ? <span style={{ color: 'orange' }}>Pending</span> : <span style={{ color: 'green' }}>Indexed</span>}
                  </td>
                  <td style={{ padding: 12 }}>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button onClick={() => handleVerify(id, rec.verified)} style={{ cursor: 'pointer', padding: '4px 8px', border: '1px solid #ccc', borderRadius: 4, background: 'white' }}>
                        {rec.verified ? 'Unverify' : 'Verify'}
                      </button>
                      <button onClick={() => handleDelete(id)} style={{ cursor: 'pointer', padding: '4px 8px', border: '1px solid #ffcccc', borderRadius: 4, background: '#fff0f0', color: 'red' }}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
