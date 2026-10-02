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
  const [message, setMessage] = useState('')
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
    setMessage('')
    try {
      await api.createAppointment({
        professor_id: professor.professor_id,
        date,
        start_time: time,
        reason,
        student_id: studentId,
        student_name: studentName,
      })
      setMessage('Request submitted. It is pending professor approval, not yet confirmed.')
    } catch (exception) {
      setError(exception.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section className="appointment-modal" role="dialog" aria-modal="true" aria-labelledby="request-title">
        <div className="modal-heading">
          <div>
            <p className="eyebrow">PROFESSOR REQUEST</p>
            <h2 id="request-title">Meet {professor.name}</h2>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close"><X size={19} /></button>
        </div>
        <form onSubmit={submit} className="request-form">
          <label>
            Date
            <input required type="date" min={tomorrow} value={date} onChange={(event) => setDate(event.target.value)} />
          </label>
          <label>
            Available 30-minute slot
            <select required value={time} onChange={(event) => setTime(event.target.value)} disabled={!slots.length}>
              <option value="">{slots.length ? 'Choose a slot' : 'No available slots'}</option>
              {slots.map((slot) => (
                <option key={slot.start_time} value={slot.start_time}>{slot.start_time}–{slot.end_time}</option>
              ))}
            </select>
          </label>
          <label>
            Reason
            <textarea required minLength="2" maxLength="500" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="What would you like to discuss?" />
          </label>
          {error && <p className="form-error">{error}</p>}
          {message && <p className="form-success">{message}</p>}
          <button className="primary-action" disabled={busy || !slots.length || !!message}>
            <CalendarDays size={16} /> {busy ? 'Submitting…' : 'Submit request'}
          </button>
        </form>
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
