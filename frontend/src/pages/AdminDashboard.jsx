import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'
import {
  RefreshCw, Users, MessageSquare, Database, FileText, Shield,
  Search, Plus, Edit2, X, Archive, RotateCcw,
  Trash2, Eye, AlertCircle, CheckCircle, Clock,
  Activity, BookOpen, Building, Wrench, Cpu, ClipboardList
} from 'lucide-react'

const TABS = [
  { id: 'overview',     label: 'Overview',      icon: Activity },
  { id: 'knowledge',    label: 'Knowledge',      icon: BookOpen },
  { id: 'rag',          label: 'RAG',            icon: Database },
  { id: 'faculty',      label: 'Faculty',        icon: Users },
  { id: 'departments',  label: 'Departments',    icon: Building },
  { id: 'facilities',   label: 'Facilities',     icon: Wrench },
  { id: 'users',        label: 'Users',          icon: Shield },
  { id: 'appointments', label: 'Appointments',   icon: MessageSquare },
  { id: 'ai',           label: 'AI Analytics',   icon: Cpu },
  { id: 'agent',        label: 'Agent',          icon: Cpu },
  { id: 'audit',        label: 'Audit Logs',     icon: ClipboardList },
  { id: 'health',       label: 'System Health',  icon: Activity },
]

function StatCard({ icon: Icon, label, value, sub, color = '#163d31' }) {
  return (
    <div style={{ background: 'white', borderRadius: 12, padding: 20, border: '1px solid #e8f1d3', boxShadow: '0 2px 8px rgba(0,0,0,.04)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, color: '#666' }}>
        <Icon size={18} /> <span style={{ fontWeight: 600, fontSize: 13 }}>{label}</span>
      </div>
      <div style={{ fontSize: 30, fontWeight: 'bold', color }}>{value ?? 0}</div>
      {sub && <div style={{ fontSize: 12, color: '#888', marginTop: 6 }}>{sub}</div>}
    </div>
  )
}

function Badge({ text, color = '#163d31', bg = '#e8f1d3' }) {
  return <span style={{ background: bg, color, borderRadius: 4, padding: '2px 7px', fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' }}>{text}</span>
}

function StatusBadge({ status }) {
  const map = { INDEXED: ['#166534', '#dcfce7'], INDEX_PENDING: ['#92400e', '#fef3c7'], INDEX_FAILED: ['#991b1b', '#fee2e2'] }
  const [c, b] = map[status] || ['#555', '#eee']
  return <Badge text={status || 'UNKNOWN'} color={c} bg={b} />
}

function SearchInput({ value, onChange, placeholder = 'Search…' }) {
  return (
    <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
      <Search size={14} style={{ position: 'absolute', left: 10, color: '#888' }} />
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        style={{ paddingLeft: 32, paddingRight: 10, paddingTop: 7, paddingBottom: 7, border: '1px solid #ddd', borderRadius: 8, fontSize: 13, outline: 'none', minWidth: 200 }} />
    </div>
  )
}

function Btn({ id, onClick, children, disabled, variant = 'default', size = 'sm' }) {
  const styles = {
    default: { background: 'white', border: '1px solid #ccc', color: '#333' },
    primary: { background: '#163d31', border: 'none', color: 'white' },
    danger:  { background: '#fee2e2', border: '1px solid #fca5a5', color: '#991b1b' },
    warn:    { background: '#fef3c7', border: '1px solid #fcd34d', color: '#92400e' },
    success: { background: '#dcfce7', border: '1px solid #86efac', color: '#166534' },
  }
  const pad = size === 'sm' ? '5px 10px' : '9px 18px'
  return (
    <button id={id} onClick={onClick} disabled={disabled}
      style={{ ...styles[variant], padding: pad, borderRadius: 7, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? .6 : 1, fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      {children}
    </button>
  )
}

function Table({ cols, rows }) {
  if (!rows.length) return <p style={{ color: '#888', marginTop: 16, fontSize: 13 }}>No data available.</p>
  return (
    <div style={{ overflowX: 'auto', background: 'white', borderRadius: 10, border: '1px solid #eee' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 13 }}>
        <thead>
          <tr style={{ background: '#f9faf7', borderBottom: '1px solid #eee' }}>
            {cols.map(c => <th key={c.key} style={{ padding: '10px 12px', fontWeight: 600, color: '#444' }}>{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #f5f5f5' }}>
              {cols.map(c => <td key={c.key} style={{ padding: '9px 12px', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.render ? c.render(row) : (row[c.key] ?? '—')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Modal({ title, onClose, children }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.4)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: 'white', borderRadius: 12, padding: 24, maxWidth: 640, width: '90vw', maxHeight: '80vh', overflowY: 'auto', position: 'relative' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <Btn onClick={onClose}><X size={14} /></Btn>
        </div>
        {children}
      </div>
    </div>
  )
}

function DayFilter({ days, setDays }) {
  return (
    <div style={{ display: 'flex', gap: 6 }}>
      {[7, 30, 90].map(d => (
        <button key={d} onClick={() => setDays(d)}
          style={{ padding: '4px 12px', borderRadius: 20, border: '1px solid', fontSize: 12, cursor: 'pointer', borderColor: days === d ? '#163d31' : '#ccc', background: days === d ? '#163d31' : 'white', color: days === d ? 'white' : '#555' }}>
          Last {d}d
        </button>
      ))}
    </div>
  )
}

// ===== OVERVIEW TAB =====
function OverviewTab({ data }) {
  if (!data) return null
  const { users, knowledge: kn, appointments: ap, ai } = data
  return (
    <div>
      <h3 style={{ marginTop: 0, color: '#163d31' }}>System Overview</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 14, marginBottom: 24 }}>
        <StatCard icon={Users} label="Total Users" value={users.total}
          sub={`${users.students} students · ${users.professors} professors · ${users.admins} admins`} />
        <StatCard icon={FileText} label="Knowledge Records" value={kn.total}
          sub={`${kn.verified} verified · ${kn.pending} pending · ${kn.archived} archived`} />
        <StatCard icon={MessageSquare} label="Total Appointments" value={ap.total}
          sub={`${ap.pending} pending · ${ap.approved} approved · ${ap.completed} completed`} />
        <StatCard icon={Cpu} label="AI Queries" value={ai.total_queries}
          sub={Object.entries(ai.by_language || {}).map(([l, c]) => `${l}: ${c}`).join(' · ')} />
      </div>
      <h4 style={{ color: '#163d31' }}>AI Queries by Intent</h4>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {Object.entries(ai.by_intent || {}).map(([intent, count]) => (
          <div key={intent} style={{ background: 'white', border: '1px solid #e8f1d3', borderRadius: 8, padding: '8px 14px', display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontWeight: 600, fontSize: 12, color: '#163d31' }}>{intent}</span>
            <Badge text={count} />
          </div>
        ))}
        {!Object.keys(ai.by_intent || {}).length && <span style={{ color: '#888', fontSize: 13 }}>No queries yet — start a chat to generate data.</span>}
      </div>
      <h4 style={{ color: '#163d31', marginTop: 20 }}>Appointments by Status</h4>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {Object.entries(ap).filter(([k]) => k !== 'total').map(([status, count]) => (
          <div key={status} style={{ background: 'white', border: '1px solid #e8f1d3', borderRadius: 8, padding: '8px 14px', display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontWeight: 600, fontSize: 12, color: '#163d31' }}>{status.toUpperCase()}</span>
            <Badge text={count} />
          </div>
        ))}
      </div>
    </div>
  )
}

// ===== KNOWLEDGE TAB =====
function KnowledgeTab() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState('all')
  const [selected, setSelected] = useState(null)
  const [editing, setEditing] = useState(null)
  const [creating, setCreating] = useState(false)
  const emptyRec = { title: '', content: '', kind: 'general', department: '', source: '', source_url: '', language: 'English', verified: false }
  const [newRec, setNewRec] = useState(emptyRec)

  const FILTERS = ['all', 'verified', 'unverified', 'indexed', 'pending', 'failed', 'archived']

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (q) params.set('q', q)
      if (filter !== 'all') params.set('filter', filter)
      setRecords(await api.get(`/admin/knowledge?${params}`))
    } catch (e) { alert('Failed to load: ' + e.message) }
    finally { setLoading(false) }
  }, [q, filter])

  useEffect(() => { load() }, [load])

  async function doAction(id, endpoint) {
    try { await api.post(`/admin/knowledge/${id}/${endpoint}`); load() }
    catch (e) { alert('Failed: ' + e.message) }
  }

  async function saveEdit() {
    const id = editing.id || editing.source
    try { await api.patch(`/admin/knowledge/${id}`, editing); setEditing(null); load() }
    catch (e) { alert('Save failed: ' + e.message) }
  }

  async function doCreate() {
    try { await api.post('/admin/knowledge', newRec); setCreating(false); setNewRec(emptyRec); load() }
    catch (e) { alert('Create failed: ' + e.message) }
  }

  async function doDelete(id) {
    if (!window.confirm('Permanently delete? Consider archiving instead.')) return
    try { await api.delete(`/admin/knowledge/${id}`); load() }
    catch (e) { alert('Delete failed: ' + e.message) }
  }

  const cols = [
    { key: 't', label: 'Title', render: r => { const rec = r.original_record || {}; return rec.name || rec.title || r.content?.slice(0, 40) || '—' } },
    { key: 'kind', label: 'Kind', render: r => <Badge text={r.kind || '?'} /> },
    { key: 'dept', label: 'Dept', render: r => (r.original_record || {}).department || r.department || '—' },
    { key: 'v', label: 'Verified', render: r => (r.original_record || {}).verified ? <Badge text="Yes" color="#166534" bg="#dcfce7" /> : <Badge text="No" color="#991b1b" bg="#fee2e2" /> },
    { key: 'idx', label: 'Index', render: r => <StatusBadge status={r.index_status} /> },
    {
      key: 'acts', label: 'Actions', render: r => {
        const id = r.id || r.source
        const verified = (r.original_record || {}).verified
        return (
          <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
            <Btn onClick={() => setSelected(r)}><Eye size={11} /></Btn>
            <Btn onClick={() => setEditing({ ...r, id })}><Edit2 size={11} /></Btn>
            <Btn variant={verified ? 'warn' : 'success'} onClick={() => doAction(id, verified ? 'unverify' : 'verify')}>{verified ? 'Unverify' : 'Verify'}</Btn>
            {r.archived
              ? <Btn variant="success" onClick={() => doAction(id, 'restore')}><RotateCcw size={11} /> Restore</Btn>
              : <Btn variant="warn" onClick={() => doAction(id, 'archive')}><Archive size={11} /> Archive</Btn>}
            <Btn variant="danger" onClick={() => doDelete(id)}><Trash2 size={11} /></Btn>
          </div>
        )
      }
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Knowledge Management ({records.length})</h3>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <SearchInput value={q} onChange={setQ} placeholder="Search records…" />
          <Btn onClick={load} disabled={loading}><RefreshCw size={12} /></Btn>
          <Btn id="knowledge-create-btn" variant="primary" onClick={() => setCreating(true)}><Plus size={12} /> New Record</Btn>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 5, marginBottom: 12, flexWrap: 'wrap' }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)}
            style={{ padding: '3px 10px', borderRadius: 20, border: '1px solid', fontSize: 11, cursor: 'pointer', borderColor: filter === f ? '#163d31' : '#ccc', background: filter === f ? '#163d31' : 'white', color: filter === f ? 'white' : '#555' }}>
            {f}
          </button>
        ))}
      </div>
      {loading ? <p>Loading records…</p> : <Table cols={cols} rows={records} />}

      {selected && (
        <Modal title="Record Details" onClose={() => setSelected(null)}>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 11, maxHeight: 400, overflowY: 'auto' }}>
            {JSON.stringify({ ...selected, embedding: '[omitted]' }, null, 2)}
          </pre>
        </Modal>
      )}

      {editing && (
        <Modal title="Edit Record" onClose={() => setEditing(null)}>
          <RecordForm rec={editing} setRec={setEditing} />
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <Btn variant="primary" onClick={saveEdit}>Save Changes</Btn>
            <Btn onClick={() => setEditing(null)}>Cancel</Btn>
          </div>
        </Modal>
      )}

      {creating && (
        <Modal title="Create Knowledge Record" onClose={() => setCreating(false)}>
          <RecordForm rec={newRec} setRec={setNewRec} />
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <Btn id="knowledge-create-submit" variant="primary" onClick={doCreate}>Create Record</Btn>
            <Btn onClick={() => setCreating(false)}>Cancel</Btn>
          </div>
        </Modal>
      )}
    </div>
  )
}

function RecordForm({ rec, setRec }) {
  const F = (label, key, id, rows) => (
    <label style={{ display: 'block', marginBottom: 8 }}>
      <span style={{ fontSize: 12, fontWeight: 600, color: '#444', display: 'block', marginBottom: 3 }}>{label}</span>
      {rows
        ? <textarea id={id} value={rec[key] || ''} rows={rows} onChange={e => setRec(r => ({ ...r, [key]: e.target.value }))}
          style={{ width: '100%', padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6, fontSize: 12, boxSizing: 'border-box' }} />
        : <input id={id} value={rec[key] || ''} onChange={e => setRec(r => ({ ...r, [key]: e.target.value }))}
          style={{ width: '100%', padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6, fontSize: 12, boxSizing: 'border-box' }} />
      }
    </label>
  )
  return (
    <div>
      {F('Title / Name', 'title', 'record-form-title')}
      {F('Content', 'content', 'record-form-content', 4)}
      {F('Kind (e.g. department, facility, faculty, general)', 'kind', 'record-form-kind')}
      {F('Department', 'department', 'record-form-dept')}
      {F('Source identifier', 'source', 'record-form-source')}
      {F('Source URL', 'source_url', 'record-form-url')}
      {F('Language', 'language', 'record-form-lang')}
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginTop: 6 }}>
        <input id="record-form-verified" type="checkbox" checked={!!rec.verified} onChange={e => setRec(r => ({ ...r, verified: e.target.checked }))} />
        Mark as Verified
      </label>
    </div>
  )
}


// ===== RAG TAB =====
function RAGTab() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [reindexing, setReindexing] = useState(false)
  const [previewQuery, setPreviewQuery] = useState('')
  const [previewResult, setPreviewResult] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const PRESETS = [
    'What is the CSE Data Science department?',
    'Who is the CSE Data Science HOD?',
    'What facilities are available?',
    'RGMCET lo library undi?',
    'కళాశాలలో ఏ విభాగాలు ఉన్నాయి?',
  ]

  const loadStatus = useCallback(async () => {
    setLoading(true)
    try { setStatus(await api.get('/admin/rag/status')) }
    catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { loadStatus() }, [loadStatus])

  async function doReindex() {
    if (!window.confirm('Re-index pending knowledge records? This may take a moment.')) return
    setReindexing(true)
    try {
      const res = await api.post('/admin/rag/reindex')
      alert(`Done. Processed: ${res.records_processed}, Indexed: ${res.records_indexed}`)
      loadStatus()
    } catch (e) { alert('Reindex failed: ' + e.message) }
    finally { setReindexing(false) }
  }

  async function runPreview(q) {
    const query = q || previewQuery
    if (!query.trim()) return
    setPreviewQuery(query)
    setPreviewLoading(true)
    setPreviewResult(null)
    try { setPreviewResult(await api.post('/admin/rag/query-preview', { query })) }
    catch (e) { setPreviewResult({ error: e.message }) }
    finally { setPreviewLoading(false) }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>RAG Management</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <Btn onClick={loadStatus} disabled={loading}><RefreshCw size={12} /> Refresh</Btn>
          <Btn id="rag-reindex-btn" variant="primary" onClick={doReindex} disabled={reindexing}>{reindexing ? 'Indexing…' : 'Re-index Now'}</Btn>
        </div>
      </div>

      {status && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(120px,1fr))', gap: 12, marginBottom: 24 }}>
          <StatCard icon={FileText} label="Total" value={status.total} />
          <StatCard icon={CheckCircle} label="Indexed" value={status.indexed} color="#166534" />
          <StatCard icon={Clock} label="Pending" value={status.pending} color="#92400e" />
          <StatCard icon={AlertCircle} label="Failed" value={status.failed} color="#991b1b" />
          <StatCard icon={Archive} label="Archived" value={status.archived} color="#555" />
        </div>
      )}

      <h4 style={{ marginBottom: 8 }}>RAG Query Preview</h4>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 10 }}>
        {PRESETS.map(q => (
          <button key={q} onClick={() => runPreview(q)}
            style={{ fontSize: 11, padding: '4px 10px', border: '1px solid #ccc', borderRadius: 20, cursor: 'pointer', background: 'white' }}>{q}</button>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input id="rag-preview-input" value={previewQuery} onChange={e => setPreviewQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && runPreview()}
          placeholder="Enter a query to preview RAG response…"
          style={{ flex: 1, padding: '8px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 13 }} />
        <Btn id="rag-preview-btn" variant="primary" onClick={() => runPreview()} disabled={previewLoading}>
          {previewLoading ? 'Running…' : 'Run Preview'}
        </Btn>
      </div>

      {previewResult && (
        <div style={{ background: 'white', borderRadius: 10, border: '1px solid #e8f1d3', padding: 16, fontSize: 13 }}>
          {previewResult.error
            ? <p style={{ color: 'red' }}>Error: {previewResult.error}</p>
            : <>
              <p><strong>Query:</strong> {previewResult.query}</p>
              <p><strong>Language:</strong> {previewResult.detected_language} · <strong>Intent:</strong> {previewResult.intent || '—'} · <strong>Verified:</strong> {previewResult.verified ? 'Yes' : 'No'}</p>
              <p><strong>Response:</strong></p>
              <div style={{ background: '#f9faf7', borderRadius: 8, padding: 12, fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 300, overflowY: 'auto' }}>
                {previewResult.response || '(no response)'}
              </div>
              {previewResult.sources?.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <strong>Sources:</strong>
                  {previewResult.sources.map((s, i) => <div key={i} style={{ fontSize: 11, color: '#555' }}>· {s.title || s.url || JSON.stringify(s)}</div>)}
                </div>
              )}
            </>
          }
        </div>
      )}
    </div>
  )
}

// ===== GENERIC LIST TAB =====
function ListTab({ title, tabId, endpoint, cols }) {
  const [rows, setRows] = useState([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try { setRows(await api.get(`/admin/${endpoint}${q ? `?q=${encodeURIComponent(q)}` : ''}`)) }
    catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }, [q, endpoint])

  useEffect(() => { load() }, [load])

  return (
    <div id={`admin-${tabId}`}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>{title}</h3>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <SearchInput value={q} onChange={setQ} />
          <Btn onClick={load} disabled={loading}><RefreshCw size={12} /></Btn>
        </div>
      </div>
      {loading ? <p>Loading…</p> : <Table cols={cols} rows={rows} />}
    </div>
  )
}

// ===== USERS TAB =====
function UsersTab() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [roleFilter, setRoleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [actionBusy, setActionBusy] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get(`/admin/users${roleFilter !== 'all' ? `?role=${roleFilter}` : ''}`)
      setRows(data)
    }
    catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }, [roleFilter])

  useEffect(() => { load() }, [load])

  const handleStatusChange = async (userId, newStatus) => {
    setActionBusy(userId)
    try {
      await api.patch(`/admin/users/${userId}/status`, { status: newStatus })
      await load()
    } catch (e) {
      alert(e.message)
    } finally {
      setActionBusy('')
    }
  }

  const filteredRows = rows.filter(r => {
    if (statusFilter !== 'all') {
      const st = r.approval_status || (r.role === 'professor' ? 'PENDING' : 'APPROVED')
      if (st !== statusFilter) return false
    }
    return true
  })

  const cols = [
    { key: 'name', label: 'Name', render: r => <strong>{r.name || '—'}</strong> },
    { key: 'email', label: 'Email', render: r => r.email || '—' },
    { key: 'department', label: 'Department', render: r => r.department || 'General' },
    { key: 'role', label: 'Role', render: r => <Badge text={(r.role || '').toUpperCase()} color={r.role === 'admin' ? '#7c3aed' : r.role === 'professor' ? '#1a5f8a' : '#163d31'} bg={r.role === 'admin' ? '#ede9fe' : r.role === 'professor' ? '#c8e6f8' : '#e8f1d3'} /> },
    {
      key: 'approval_status',
      label: 'Approval Status',
      render: r => {
        const st = r.approval_status || (r.role === 'professor' ? 'PENDING' : 'APPROVED')
        const colorMap = {
          APPROVED: ['#166534', '#dcfce7'],
          PENDING: ['#92400e', '#fef3c7'],
          REJECTED: ['#991b1b', '#fee2e2'],
          SUSPENDED: ['#4b5563', '#f3f4f6'],
        }
        const [c, bg] = colorMap[st] || ['#555', '#eee']
        return <Badge text={st} color={c} bg={bg} />
      }
    },
    { key: 'user_id', label: 'User ID', render: r => <code style={{ fontSize: 11 }}>{r.user_id}</code> },
    {
      key: 'actions',
      label: 'Actions',
      render: r => {
        if (r.role !== 'professor') return <span style={{ color: '#888', fontSize: 12 }}>—</span>
        const st = r.approval_status || 'PENDING'
        const isBusy = actionBusy === r.user_id
        return (
          <div style={{ display: 'flex', gap: 6 }}>
            {st === 'PENDING' && (
              <>
                <button
                  id={`approve-user-${r.user_id}`}
                  onClick={() => handleStatusChange(r.user_id, 'APPROVED')}
                  disabled={isBusy}
                  style={{ background: '#166534', color: 'white', border: 'none', padding: '4px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}
                >
                  Approve
                </button>
                <button
                  id={`reject-user-${r.user_id}`}
                  onClick={() => handleStatusChange(r.user_id, 'REJECTED')}
                  disabled={isBusy}
                  style={{ background: '#991b1b', color: 'white', border: 'none', padding: '4px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}
                >
                  Reject
                </button>
              </>
            )}
            {st === 'APPROVED' && (
              <button
                id={`suspend-user-${r.user_id}`}
                onClick={() => handleStatusChange(r.user_id, 'SUSPENDED')}
                disabled={isBusy}
                style={{ background: '#f59e0b', color: 'white', border: 'none', padding: '4px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}
              >
                Suspend
              </button>
            )}
            {(st === 'REJECTED' || st === 'SUSPENDED') && (
              <button
                id={`reactivate-user-${r.user_id}`}
                onClick={() => handleStatusChange(r.user_id, 'APPROVED')}
                disabled={isBusy}
                style={{ background: '#166534', color: 'white', border: 'none', padding: '4px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}
              >
                Approve
              </button>
            )}
          </div>
        )
      }
    }
  ]

  return (
    <div id="admin-users">
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0 }}>User & Professor Account Management</h3>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {['all', 'student', 'professor', 'admin'].map(r => (
            <button key={r} onClick={() => setRoleFilter(r)}
              style={{ padding: '4px 12px', borderRadius: 20, border: '1px solid', fontSize: 12, cursor: 'pointer', borderColor: roleFilter === r ? '#163d31' : '#ccc', background: roleFilter === r ? '#163d31' : 'white', color: roleFilter === r ? 'white' : '#555' }}>
              {r}
            </button>
          ))}
          {roleFilter === 'professor' && ['all', 'PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED'].map(st => (
            <button key={st} onClick={() => setStatusFilter(st)}
              style={{ padding: '4px 10px', borderRadius: 14, border: '1px solid', fontSize: 11, cursor: 'pointer', borderColor: statusFilter === st ? '#1a5f8a' : '#ddd', background: statusFilter === st ? '#1a5f8a' : '#f9f9f9', color: statusFilter === st ? 'white' : '#444' }}>
              {st}
            </button>
          ))}
          <Btn onClick={load} disabled={loading}><RefreshCw size={12} /></Btn>
        </div>
      </div>
      {loading ? <p>Loading…</p> : <Table cols={cols} rows={filteredRows} />}
    </div>
  )
}

// ===== APPOINTMENTS TAB =====
function AppointmentsTab() {
  const [viewMode, setViewMode] = useState('list') // 'list' or 'analytics'
  const [appointments, setAppointments] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [days, setDays] = useState(30)
  const [overrideBusy, setOverrideBusy] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [appts, anal] = await Promise.all([
        api.get(`/admin/appointments${statusFilter !== 'ALL' ? `?status=${statusFilter}` : ''}${searchQuery ? `&q=${encodeURIComponent(searchQuery)}` : ''}`),
        api.get(`/admin/appointments/analytics?days=${days}`),
      ])
      setAppointments(appts || [])
      setAnalytics(anal)
    }
    catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }, [statusFilter, searchQuery, days])

  useEffect(() => { load() }, [load])

  const handleOverride = async (appointmentId, targetStatus) => {
    const reason = window.prompt(`Admin override: reason for setting ${appointmentId} to ${targetStatus}?`, 'Administrative update')
    if (reason === null) return
    setOverrideBusy(appointmentId)
    try {
      await api.patch(`/admin/appointments/${appointmentId}/override`, { status: targetStatus, reason })
      await load()
    } catch (e) {
      alert(e.message)
    } finally {
      setOverrideBusy('')
    }
  }

  const cols = [
    { key: 'appointment_id', label: 'ID', render: r => <code style={{ fontSize: 11 }}>{r.appointment_id}</code> },
    {
      key: 'student',
      label: 'Student',
      render: r => (
        <div>
          <strong>{r.student_name || 'Student'}</strong>
          <div style={{ fontSize: 11, color: '#666' }}>{r.student_id}</div>
        </div>
      )
    },
    {
      key: 'professor',
      label: 'Professor',
      render: r => (
        <div>
          <strong>{r.professor_name || 'Professor'}</strong>
          <div style={{ fontSize: 11, color: '#666' }}>{r.department || 'RGMCET'}</div>
        </div>
      )
    },
    {
      key: 'datetime',
      label: 'Date & Time',
      render: r => (
        <div>
          <span>{r.date}</span>
          <div style={{ fontSize: 11, color: '#666' }}>{r.start_time} – {r.end_time}</div>
        </div>
      )
    },
    {
      key: 'reason',
      label: 'Purpose',
      render: r => <span title={r.reason}>{r.reason?.slice(0, 40)}{r.reason?.length > 40 ? '…' : ''}</span>
    },
    {
      key: 'status',
      label: 'Status',
      render: r => {
        const st = r.status || 'UNKNOWN'
        const colorMap = {
          APPROVED: ['#166534', '#dcfce7'],
          PENDING_APPROVAL: ['#92400e', '#fef3c7'],
          PENDING: ['#92400e', '#fef3c7'],
          REJECTED: ['#991b1b', '#fee2e2'],
          CANCELLED: ['#6b7280', '#f3f4f6'],
        }
        const [c, bg] = colorMap[st] || ['#555', '#eee']
        return <Badge text={st.replace('_', ' ')} color={c} bg={bg} />
      }
    },
    {
      key: 'calendar',
      label: 'Calendar Sync',
      render: r => r.calendar_event_id ? (
        <span style={{ color: '#166534', fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
          <CheckCircle size={12} /> Synced
        </span>
      ) : <span style={{ color: '#888', fontSize: 11 }}>—</span>
    },
    {
      key: 'actions',
      label: 'Admin Override',
      render: r => {
        const isBusy = overrideBusy === r.appointment_id
        return (
          <div style={{ display: 'flex', gap: 4 }}>
            {r.status !== 'APPROVED' && (
              <button
                id={`admin-approve-${r.appointment_id}`}
                onClick={() => handleOverride(r.appointment_id, 'APPROVED')}
                disabled={isBusy}
                style={{ background: '#166534', color: 'white', border: 'none', padding: '3px 7px', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                title="Admin Approve"
              >
                Approve
              </button>
            )}
            {r.status !== 'REJECTED' && (
              <button
                id={`admin-reject-${r.appointment_id}`}
                onClick={() => handleOverride(r.appointment_id, 'REJECTED')}
                disabled={isBusy}
                style={{ background: '#991b1b', color: 'white', border: 'none', padding: '3px 7px', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                title="Admin Reject"
              >
                Reject
              </button>
            )}
            {r.status !== 'CANCELLED' && (
              <button
                id={`admin-cancel-${r.appointment_id}`}
                onClick={() => handleOverride(r.appointment_id, 'CANCELLED')}
                disabled={isBusy}
                style={{ background: '#4b5563', color: 'white', border: 'none', padding: '3px 7px', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}
                title="Admin Cancel"
              >
                Cancel
              </button>
            )}
          </div>
        )
      }
    }
  ]

  return (
    <div id="admin-appointments">
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0 }}>Appointments Management</h3>
        <div style={{ display: 'flex', gap: 6, marginLeft: 16 }}>
          <button
            onClick={() => setViewMode('list')}
            style={{ padding: '5px 12px', borderRadius: 6, border: '1px solid #163d31', background: viewMode === 'list' ? '#163d31' : 'white', color: viewMode === 'list' ? 'white' : '#163d31', fontSize: 12, cursor: 'pointer', fontWeight: 600 }}
          >
            All Appointments ({appointments.length})
          </button>
          <button
            onClick={() => setViewMode('analytics')}
            style={{ padding: '5px 12px', borderRadius: 6, border: '1px solid #163d31', background: viewMode === 'analytics' ? '#163d31' : 'white', color: viewMode === 'analytics' ? 'white' : '#163d31', fontSize: 12, cursor: 'pointer', fontWeight: 600 }}
          >
            Analytics & Trends
          </button>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          {viewMode === 'analytics' ? (
            <DayFilter days={days} setDays={setDays} />
          ) : (
            <>
              <SearchInput value={searchQuery} onChange={setSearchQuery} placeholder="Search student/professor/ID…" />
              <Btn onClick={load} disabled={loading}><RefreshCw size={12} /></Btn>
            </>
          )}
        </div>
      </div>

      {viewMode === 'list' ? (
        <div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
            {['ALL', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'CANCELLED'].map(st => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                style={{
                  padding: '4px 12px',
                  borderRadius: 20,
                  border: '1px solid',
                  fontSize: 12,
                  cursor: 'pointer',
                  borderColor: statusFilter === st ? '#163d31' : '#ccc',
                  background: statusFilter === st ? '#163d31' : 'white',
                  color: statusFilter === st ? 'white' : '#555'
                }}
              >
                {st.replace('_', ' ')}
              </button>
            ))}
          </div>
          {loading ? <p>Loading…</p> : <Table cols={cols} rows={appointments} />}
        </div>
      ) : (
        loading ? <p>Loading…</p> : analytics && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(120px,1fr))', gap: 12, marginBottom: 20 }}>
              {Object.entries(analytics.by_status || {}).map(([s, c]) => (
                <StatCard key={s} icon={MessageSquare} label={s.replace('_', ' ')} value={c} />
              ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div>
                <h4>By Professor</h4>
                {Object.entries(analytics.by_professor || {}).length
                  ? Object.entries(analytics.by_professor).map(([n, c]) => (
                    <div key={n} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f5f5f5', fontSize: 13 }}>
                      <span>{n}</span><Badge text={c} />
                    </div>
                  ))
                  : <p style={{ color: '#888', fontSize: 13 }}>No data available.</p>}
              </div>
              <div>
                <h4>By Department</h4>
                {Object.entries(analytics.by_department || {}).length
                  ? Object.entries(analytics.by_department).map(([d, c]) => (
                    <div key={d} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f5f5f5', fontSize: 13 }}>
                      <span>{d}</span><Badge text={c} />
                    </div>
                  ))
                  : <p style={{ color: '#888', fontSize: 13 }}>No data available.</p>}
              </div>
            </div>
          </div>
        )
      )}
    </div>
  )
}

// ===== AI ANALYTICS TAB =====
function AIAnalyticsTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)

  const load = useCallback(async () => {
    setLoading(true)
    try { setData(await api.get(`/admin/ai/analytics?days=${days}`)) }
    catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }, [days])

  useEffect(() => { load() }, [load])

  return (
    <div id="admin-ai">
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0 }}>AI Query Analytics</h3>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <DayFilter days={days} setDays={setDays} />
          <Btn onClick={load} disabled={loading}><RefreshCw size={12} /></Btn>
        </div>
      </div>
      {loading ? <p>Loading…</p> : data && (
        <div>
          <div style={{ marginBottom: 20 }}>
            <StatCard icon={Cpu} label="Total AI Queries" value={data.total_queries} sub={`Period: last ${days} days`} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <h4>By Intent</h4>
              {Object.entries(data.by_intent || {}).length
                ? Object.entries(data.by_intent).map(([intent, cnt]) => (
                  <div key={intent} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f5f5f5', fontSize: 13 }}>
                    <span>{intent}</span><Badge text={cnt} />
                  </div>
                ))
                : <p style={{ color: '#888', fontSize: 13 }}>No data available.</p>}
            </div>
            <div>
              <h4>By Language</h4>
              {Object.entries(data.by_language || {}).length
                ? Object.entries(data.by_language).map(([lang, cnt]) => (
                  <div key={lang} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f5f5f5', fontSize: 13 }}>
                    <span>{lang}</span><Badge text={cnt} />
                  </div>
                ))
                : <p style={{ color: '#888', fontSize: 13 }}>No data available.</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ===== AGENT INSPECTION TAB =====
function AgentTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try { setData(await api.get('/admin/agent/status')) }
    catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div id="admin-agent">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>AI Agent Inspection</h3>
        <Btn onClick={load} disabled={loading}><RefreshCw size={12} /> Refresh</Btn>
      </div>
      {loading ? <p>Loading…</p> : data && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 12, marginBottom: 24 }}>
            <StatCard icon={Cpu} label="Agent Status" value={data.agent_status?.toUpperCase()} color={data.agent_status === 'active' ? '#166534' : '#991b1b'} />
            <StatCard icon={Activity} label="Available Tools" value={data.tool_count} />
            <StatCard icon={CheckCircle} label="Max Steps/Turn" value={data.max_steps_per_turn} />
          </div>

          <h4 style={{ color: '#163d31', marginBottom: 12 }}>Available Tools</h4>
          <div style={{ display: 'grid', gap: 10, marginBottom: 24 }}>
            {(data.tools || []).map(tool => (
              <div key={tool.name} style={{ background: 'white', border: '1px solid #e8f1d3', borderRadius: 10, padding: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <Badge text={tool.name} color="#1a5f8a" bg="#c8e6f8" />
                  {tool.required_args?.length > 0 && <span style={{ fontSize: 11, color: '#888' }}>Requires: {tool.required_args.join(', ')}</span>}
                </div>
                <p style={{ margin: 0, fontSize: 12, color: '#555' }}>{tool.description}</p>
                {tool.parameters?.length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    <span style={{ fontSize: 11, color: '#888' }}>Parameters: </span>
                    {tool.parameters.map(p => <Badge key={p} text={p} color="#555" bg="#f5f5f5" />).reduce((acc, el, i) => i === 0 ? [el] : [...acc, ' ', el], [])}
                  </div>
                )}
              </div>
            ))}
          </div>

          <h4 style={{ color: '#163d31', marginBottom: 12 }}>Supported Workflows</h4>
          <div style={{ background: 'white', border: '1px solid #e8f1d3', borderRadius: 10, padding: 14 }}>
            {(data.supported_workflows || []).map((wf, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: i < data.supported_workflows.length - 1 ? '1px solid #f5f5f5' : 'none' }}>
                <CheckCircle size={14} color="#166534" />
                <span style={{ fontSize: 13 }}>{wf}</span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 16, padding: 12, background: '#fef3c7', borderRadius: 8, fontSize: 12, color: '#92400e' }}>
            ⚠️ API keys, credentials, internal prompts, and sensitive data are never exposed through this interface.
          </div>
        </div>
      )}
    </div>
  )
}


// ===== AUDIT LOGS TAB =====
function AuditTab() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionFilter, setActionFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [days, setDays] = useState(30)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const p = new URLSearchParams({ days })
      if (actionFilter) p.set('action', actionFilter)
      if (typeFilter) p.set('target_type', typeFilter)
      setLogs(await api.get(`/admin/audit-logs?${p}`))
    } catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }, [actionFilter, typeFilter, days])

  useEffect(() => { load() }, [load])

  const cols = [
    { key: 'ts', label: 'Time', render: r => r.timestamp ? new Date(r.timestamp).toLocaleString() : '—' },
    { key: 'admin_email', label: 'Admin', render: r => r.admin_email || '—' },
    { key: 'action', label: 'Action', render: r => <Badge text={r.action} color="#1a5f8a" bg="#c8e6f8" /> },
    { key: 'target', label: 'Target', render: r => `${r.target_type} (${r.target_id})` },
    { key: 'result', label: 'Result', render: r => <Badge text={r.result} color={r.result === 'SUCCESS' ? '#166534' : '#991b1b'} bg={r.result === 'SUCCESS' ? '#dcfce7' : '#fee2e2'} /> },
  ]

  return (
    <div id="admin-audit">
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>Audit Logs</h3>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <SearchInput value={actionFilter} onChange={setActionFilter} placeholder="Filter action…" />
          <SearchInput value={typeFilter} onChange={setTypeFilter} placeholder="Filter type…" />
          <DayFilter days={days} setDays={setDays} />
          <Btn onClick={load} disabled={loading}><RefreshCw size={12} /></Btn>
        </div>
      </div>
      {loading ? <p>Loading…</p> : <Table cols={cols} rows={logs} />}
    </div>
  )
}

// ===== SYSTEM HEALTH TAB =====
function HealthTab() {
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try { setHealth(await api.get('/admin/health')) }
    catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  function Row({ label, status, detail }) {
    const ok = ['OK', 'connected', 'configured', 'demo'].includes(status)
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 0', borderBottom: '1px solid #f5f5f5' }}>
        {ok ? <CheckCircle size={16} color="#166534" /> : <AlertCircle size={16} color="#92400e" />}
        <span style={{ fontWeight: 600, minWidth: 160 }}>{label}</span>
        <Badge text={status || 'unknown'} color={ok ? '#166534' : '#92400e'} bg={ok ? '#dcfce7' : '#fef3c7'} />
        {detail && <span style={{ fontSize: 12, color: '#666' }}>{detail}</span>}
      </div>
    )
  }

  return (
    <div id="admin-health">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>System Health</h3>
        <Btn onClick={load} disabled={loading}><RefreshCw size={12} /> Refresh</Btn>
      </div>
      {loading ? <p>Loading…</p> : health && (
        <div style={{ background: 'white', borderRadius: 10, border: '1px solid #eee', padding: 16 }}>
          <Row label="Backend API" status={health.backend?.status} detail={`v${health.backend?.version}`} />
          <Row label="Database" status={health.database?.status} detail={health.database?.demo_mode ? 'Demo/in-memory mode' : 'Production'} />
          <Row label="LLM" status={health.llm?.status} detail={`Provider: ${health.llm?.provider}`} />
          <Row label="RAG / Vector Store" status={health.rag?.status} detail={`${health.rag?.indexed}/${health.rag?.total_documents} documents indexed`} />
          <Row label="Google Calendar" status={health.google_calendar?.status} detail={health.google_calendar?.note} />
          <Row label="Demo Mode" status={health.environment?.demo_mode ? 'active' : 'off'} />
        </div>
      )}
    </div>
  )
}

// ===== MAIN COMPONENT =====
export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('overview')
  const [overview, setOverview] = useState(null)
  const [loadingOv, setLoadingOv] = useState(true)
  const [errorOv, setErrorOv] = useState(null)

  const loadOverview = useCallback(async () => {
    setLoadingOv(true)
    setErrorOv(null)
    try { setOverview(await api.get('/admin/overview')) }
    catch (e) { setErrorOv(e.message) }
    finally { setLoadingOv(false) }
  }, [])

  useEffect(() => { loadOverview() }, [loadOverview])

  const facultyCols = [
    { key: 'name', label: 'Name', render: r => r.name || '—' },
    { key: 'department', label: 'Department', render: r => r.department || '—' },
    { key: 'designation', label: 'Designation', render: r => r.designation || '—' },
    { key: 'email', label: 'Email', render: r => r.email || '—' },
    { key: 'is_hod', label: 'HOD', render: r => r.is_hod ? <Badge text="HOD" color="#7c3aed" bg="#ede9fe" /> : '—' },
  ]

  const deptCols = [
    { key: 'name', label: 'Name', render: r => (r.original_record || {}).name || '—' },
    { key: 'dept', label: 'Dept', render: r => (r.original_record || {}).department || r.department || '—' },
    { key: 'src', label: 'Source', render: r => r.source_url ? <a href={r.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>Link</a> : '—' },
  ]

  const facilCols = [
    { key: 'name', label: 'Name', render: r => (r.original_record || {}).name || (r.original_record || {}).title || '—' },
    { key: 'loc', label: 'Location', render: r => (r.original_record || {}).location || '—' },
    { key: 'src', label: 'Source', render: r => r.source_url ? <a href={r.source_url} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>Link</a> : '—' },
  ]

  return (
    <div id="admin-dashboard" style={{ padding: '0 4px', minHeight: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, paddingTop: 8 }}>
        <h1 style={{ margin: 0, fontSize: 22, color: '#163d31' }}>Admin Dashboard</h1>
        <Btn onClick={loadOverview} disabled={loadingOv}><RefreshCw size={14} /> Refresh Overview</Btn>
      </div>

      {/* Tab navigation */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 24, borderBottom: '2px solid #e8f1d3', paddingBottom: 10 }}>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} id={`admin-tab-${id}`} onClick={() => setActiveTab(id)}
            style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '6px 12px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 500, background: activeTab === id ? '#163d31' : 'transparent', color: activeTab === id ? 'white' : '#555' }}>
            <Icon size={13} /> {label}
          </button>
        ))}
      </div>

      {errorOv && <div style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 8, padding: 12, color: '#991b1b', marginBottom: 16 }}>{errorOv}</div>}

      {activeTab === 'overview'     && (loadingOv ? <p>Loading…</p> : <OverviewTab data={overview} />)}
      {activeTab === 'knowledge'    && <KnowledgeTab />}
      {activeTab === 'rag'          && <RAGTab />}
      {activeTab === 'faculty'      && <ListTab title="Faculty Management" tabId="faculty" endpoint="faculty" cols={facultyCols} />}
      {activeTab === 'departments'  && <ListTab title="Departments" tabId="departments" endpoint="departments" cols={deptCols} />}
      {activeTab === 'facilities'   && <ListTab title="Facilities" tabId="facilities" endpoint="facilities" cols={facilCols} />}
      {activeTab === 'users'        && <UsersTab />}
      {activeTab === 'appointments' && <AppointmentsTab />}
      {activeTab === 'ai'           && <AIAnalyticsTab />}
      {activeTab === 'agent'        && <AgentTab />}
      {activeTab === 'audit'        && <AuditTab />}
      {activeTab === 'health'       && <HealthTab />}
    </div>
  )
}
