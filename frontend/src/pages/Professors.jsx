import { useEffect, useState } from 'react'
import { ArrowLeft, CalendarDays, X } from 'lucide-react'
import ProfessorCard, { ProfessorSearch } from '../components/ProfessorCard.jsx'
import { api, DEMO_STUDENT_ID } from '../services/api.js'
import { useAuth } from '../contexts/AuthContext.jsx'

function AppointmentModal({ professor, onClose, studentId, studentName }) {
  const tomorrow = new Date(Date.now() + 86400000).toLocaleDateString('en-CA')
  const [date, setDate] = useState(tomorrow)
  const [slots, setSlots] = useState([])
  const [time, setTime] = useState('')
  const [reason, setReason] = useState('')
  const [submittedData, setSubmittedData] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!date) return
    api.availability(professor.professor_id, date)
      .then((items) => { setSlots(items); setTime(items[0]?.start_time || '') })
      .catch((exception) => setError(exception.message))
  }, [professor.professor_id, date])

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const res = await api.createAppointment({
        professor_id: professor.professor_id,
        professor_name: professor.name,
        date,
        start_time: time,
        reason,
        student_id: studentId,
        student_name: studentName,
      })
      setSubmittedData({
        professorName: professor.name,
        department: professor.department,
        date,
        time,
        status: res.status || 'PENDING_APPROVAL',
      })
    } catch (exception) {
      setError(exception.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section className="appointment-modal appointment-dialog" role="dialog" aria-modal="true" aria-labelledby="request-title" style={{ maxWidth: '480px', width: '100%' }}>
        <div className="modal-heading">
          <div>
            <p className="eyebrow">CONSULTATION REQUEST</p>
            <h2 id="request-title">Request Appointment</h2>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close"><X size={19} /></button>
        </div>

        {submittedData ? (
          <div className="appointment-success-box" style={{ padding: '20px 0', textAlign: 'center' }}>
            <div style={{ background: '#dcfce7', color: '#166534', width: 48, height: 48, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px' }}>
              <CalendarDays size={24} />
            </div>
            <h3 style={{ fontSize: 18, marginBottom: 8, color: '#163d31' }}>
              Appointment request sent to {submittedData.professorName}.
            </h3>
            <div style={{ display: 'inline-block', margin: '8px 0 16px', background: '#fef3c7', color: '#92400e', padding: '6px 14px', borderRadius: 20, fontWeight: 700, fontSize: 13, letterSpacing: '0.03em' }}>
              Status: PENDING PROFESSOR APPROVAL
            </div>
            <p style={{ fontSize: 13, color: '#555', lineHeight: 1.5, marginBottom: 20 }}>
              Your request is now waiting in <strong>{submittedData.professorName}</strong>'s queue for review. You can monitor the approval status anytime from your <strong>Appointments</strong> dashboard.
            </p>
            <button className="primary-action" onClick={onClose} style={{ width: '100%' }}>
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={submit} className="request-form">
            <div style={{ background: '#f8faf6', padding: '12px 14px', borderRadius: 8, marginBottom: 14, border: '1px solid #e2ebd8' }}>
              <div style={{ fontSize: 13, color: '#666' }}>Professor:</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#163d31' }}>{professor.name}</div>
              <div style={{ fontSize: 13, color: '#666', marginTop: 4 }}>Department:</div>
              <div style={{ fontSize: 14, fontWeight: 500, color: '#333' }}>{professor.department || 'General'}</div>
            </div>

            <label>
              Date:
              <input id="appointment-date-input" required type="date" min={tomorrow} value={date} onChange={(event) => setDate(event.target.value)} />
            </label>
            <label>
              Time:
              <select id="appointment-time-select" required value={time} onChange={(event) => setTime(event.target.value)} disabled={!slots.length}>
                <option value="">{slots.length ? 'Select a 30-minute slot' : 'No available slots on this day'}</option>
                {slots.map((slot) => (
                  <option key={slot.start_time} value={slot.start_time}>{slot.start_time} – {slot.end_time}</option>
                ))}
              </select>
            </label>
            <label>
              Purpose:
              <textarea id="appointment-reason-input" required minLength="2" maxLength="500" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Student purpose (e.g. Project discussion, doubts, lab review)" />
            </label>
            {error && <p className="form-error">{error}</p>}
            <button id="appointment-submit-button" className="primary-action" disabled={busy || !slots.length} style={{ width: '100%', marginTop: 8 }}>
              <CalendarDays size={16} /> {busy ? 'Sending request…' : 'Request Appointment'}
            </button>
          </form>
        )}
      </section>
    </div>
  )
}


export default function Professors() {
  const { user } = useAuth()
  const [query, setQuery] = useState('')
  const [professors, setProfessors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)

  // Use real student identity when authenticated, fall back to demo
  const studentId = (user && user.role === 'student') ? user.user_id || DEMO_STUDENT_ID : DEMO_STUDENT_ID
  const studentName = (user && user.role === 'student') ? user.name || 'Student' : 'Demo Student'

  useEffect(() => {
    let active = true
    setLoading(true)
    api.professors(query)
      .then((items) => { if (active) { setProfessors(items); setError('') } })
      .catch((exception) => { if (active) setError(exception.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [query])

  return (
    <section className="page-content">
      <div className="page-heading">
        <div>
          <p className="eyebrow">PEOPLE & OFFICE HOURS</p>
          <h1>Professors</h1>
          <p>Explore profiles and request a meeting during a published schedule.</p>
        </div>
      </div>
      <ProfessorSearch value={query} onChange={setQuery} />
      {error && <p className="form-error">{error}</p>}
      {loading
        ? <div className="loading-state">Loading directory…</div>
        : professors.length
          ? <div className="professor-grid">
              {professors.map((professor) => (
                <ProfessorCard key={professor.professor_id} professor={professor} onBook={setSelected} />
              ))}
            </div>
          : <div className="empty-state"><ArrowLeft size={18} /><p>No professor records matched your search.</p></div>
      }
      {selected && (
        <AppointmentModal
          professor={selected}
          onClose={() => setSelected(null)}
          studentId={studentId}
          studentName={studentName}
        />
      )}
    </section>
  )
}
