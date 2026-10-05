import { useEffect, useState } from 'react'
import { CalendarCheck, Check, Clock3, GraduationCap, RefreshCw, X, CalendarDays, CalendarClock } from 'lucide-react'
import { api } from '../services/api.js'
import { useAuth } from '../contexts/AuthContext.jsx'

function formatDate(value) {
  if (!value) return ''
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
}

function StatusPill({ status }) {
  const cls = { APPROVED: 'approved', REJECTED: 'rejected', CANCELLED: 'cancelled' }[status] || ''
  return <span className={`status-pill ${cls}`}>{status ? status.replaceAll('_', ' ') : 'UNKNOWN'}</span>
}

function PendingCard({ item, onApprove, onOpenReject, onOpenReschedule, isBusy, professorName, department }) {
  return (
    <article className={`dash-request-card ${isBusy ? 'row-busy' : ''}`} id={`request-${item.appointment_id}`} style={{ borderLeft: '4px solid #f59e0b' }}>
      <div className="request-student">
        <div className="request-avatar"><GraduationCap size={18} /></div>
        <div>
          <strong className="request-name"><span style={{ fontWeight: 500, color: '#666' }}>Student:</span> {item.student_name || 'Student'}</strong>
          <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
            <span>Email: <strong>{item.student_email || item.student_id}</strong></span>
          </div>
        </div>
      </div>
      <div className="request-details">
        <div style={{ fontSize: 13, marginBottom: 4, color: '#333' }}>
          <strong>Professor:</strong> {item.professor_name || professorName || 'Dr. B. Bhaskara Rao'}
        </div>
        <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
          <strong>Department:</strong> {item.department || department || 'CSE (Data Science)'}
        </div>
        <div className="request-when">
          <strong>Date:</strong> {formatDate(item.date)} | <strong>Time:</strong> {item.start_time} – {item.end_time || '30 mins'}
        </div>
        <p className="request-reason"><strong>Purpose:</strong> {item.reason}</p>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#92400e', background: '#fef3c7', padding: '3px 8px', borderRadius: 4 }}>
            Status: PENDING
          </span>
          <span style={{ fontSize: 11, color: '#666', fontStyle: 'italic' }}>
            Assigned to: {item.professor_name || professorName || 'You'}
          </span>
        </div>
      </div>
      <div className="request-actions" style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
        <button
          id={`approve-btn-${item.appointment_id}`}
          className="primary-action approve-action approve-button"
          onClick={() => onApprove(item.appointment_id)}
          disabled={isBusy}
          aria-label={`Approve appointment from ${item.student_name}`}
        >
          <Check size={16} /> Approve
        </button>
        <button
          id={`reject-btn-${item.appointment_id}`}
          className="outline-action reject-action"
          onClick={() => onOpenReject(item)}
          disabled={isBusy}
          aria-label={`Reject appointment from ${item.student_name}`}
        >
          <X size={16} /> Reject
        </button>
        <button
          id={`reschedule-btn-${item.appointment_id}`}
          className="outline-action"
          onClick={() => onOpenReschedule(item)}
          disabled={isBusy}
          style={{ fontSize: 12, padding: '5px 10px' }}
          aria-label={`Reschedule appointment from ${item.student_name}`}
        >
          <CalendarClock size={15} /> Reschedule
        </button>
      </div>
    </article>
  )
}

export default function ProfessorDashboard() {
  const { user } = useAuth()
  const [profInfo, setProfInfo] = useState({})
  const [pending, setPending] = useState([])
  const [upcoming, setUpcoming] = useState([])
  const [history, setHistory] = useState([])
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [busyId, setBusyId] = useState('')
  const [loading, setLoading] = useState(true)

  // Modals
  const [rejectingItem, setRejectingItem] = useState(null)
  const [rejectionReason, setRejectionReason] = useState('')
  const [reschedulingItem, setReschedulingItem] = useState(null)
  const [newDate, setNewDate] = useState('')
  const [newTime, setNewTime] = useState('')
  const [availableSlots, setAvailableSlots] = useState([])
  const [showSchedule, setShowSchedule] = useState(false)
  const [schedule, setSchedule] = useState([])
  const [savingSchedule, setSavingSchedule] = useState(false)

  async function load() {
    setLoading(true)
    setError('')
    try {
      // Try personalized dashboard endpoint first
      try {
        const dash = await api.professorDashboard()
        setProfInfo(dash.professor || {})
        setPending(dash.pending || [])
        setUpcoming(dash.approved || [])
        const closed = [...(dash.rejected || []), ...(dash.cancelled || [])]
        setHistory(closed)
        if (dash.schedule) setSchedule(dash.schedule)
      } catch (dashErr) {
        // Fallback to separate endpoints
        const all = await api.professorAppointments()
        setPending(all.filter((a) => a.status === 'PENDING_APPROVAL'))
        setUpcoming(all.filter((a) => a.status === 'APPROVED'))
        setHistory(all.filter((a) => ['REJECTED', 'CANCELLED'].includes(a.status)))
      }
    } catch (err) {
      setError(err.message || 'Could not load professor dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function approve(id) {
    setBusyId(id)
    setError('')
    setSuccessMsg('')
    try {
      await api.decideAppointment(id, 'approve')
      setSuccessMsg('Appointment approved successfully.')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId('')
    }
  }

  async function confirmReject() {
    if (!rejectingItem) return
    const id = rejectingItem.appointment_id
    setBusyId(id)
    setError('')
    setSuccessMsg('')
    try {
      await api.rejectAppointment(id, rejectionReason)
      setRejectingItem(null)
      setRejectionReason('')
      setSuccessMsg('Appointment request rejected.')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId('')
    }
  }

  function openReschedule(item) {
    setReschedulingItem(item)
    const tomorrow = new Date(Date.now() + 86400000).toLocaleDateString('en-CA')
    setNewDate(tomorrow)
    setNewTime('')
    const profId = item.professor_id || profInfo.professor_id || user?.professor_id
    if (profId) {
      api.availability(profId, tomorrow)
        .then((slots) => {
          setAvailableSlots(slots)
          setNewTime(slots[0]?.start_time || '10:00')
        })
        .catch(() => setAvailableSlots([]))
    }
  }

  async function onDateChange(dateVal) {
    setNewDate(dateVal)
    const profId = reschedulingItem?.professor_id || profInfo.professor_id || user?.professor_id
    if (profId && dateVal) {
      try {
        const slots = await api.availability(profId, dateVal)
        setAvailableSlots(slots)
        setNewTime(slots[0]?.start_time || '')
      } catch {
        setAvailableSlots([])
      }
    }
  }

  async function confirmReschedule() {
    if (!reschedulingItem || !newDate || !newTime) return
    const id = reschedulingItem.appointment_id
    setBusyId(id)
    setError('')
    setSuccessMsg('')
    try {
      await api.rescheduleAppointment(id, newDate, newTime)
      setReschedulingItem(null)
      setSuccessMsg(`Appointment rescheduled to ${newDate} at ${newTime}.`)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId('')
    }
  }

  async function loadSchedule() {
    const profId = profInfo.professor_id || user?.professor_id
    if (!profId) {
      setSchedule([])
      setShowSchedule(true)
      return
    }
    try {
      const slots = await api.schedule(profId)
      setSchedule(slots)
      setShowSchedule(true)
    } catch (err) {
      setSchedule([])
      setShowSchedule(true)
    }
  }

  async function saveSchedule() {
    setSavingSchedule(true)
    const profId = profInfo.professor_id || user?.professor_id
    try {
      await api.updateSchedule(profId, schedule)
      setShowSchedule(false)
      setSuccessMsg('Weekly schedule updated successfully.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingSchedule(false)
    }
  }

  const total = pending.length + upcoming.length + history.length
  const displayName = profInfo.name || user?.name || 'Dr. B. Bhaskara Rao'
  const displayDept = profInfo.department || user?.department || 'CSE (Data Science)'
  const displayDesig = profInfo.designation || 'Associate Professor & HOD'
  const displayId = profInfo.professor_id || user?.professor_id || 'PROF-VERIFIED-CSEDS-002'
  const displayStatus = profInfo.approval_status || user?.approval_status || 'APPROVED'

  return (
    <section className="page-content dashboard-page">
      {/* Personalized Professor Identity Banner */}
      <div className="professor-identity-banner prof-identity-header" style={{ background: '#f4f8f2', border: '1px solid #dbe7d5', borderRadius: '12px', padding: '18px 22px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
          <div>
            <p className="eyebrow" style={{ color: '#163d31', letterSpacing: '0.08em', marginBottom: 4 }}>
              PROFESSOR PORTAL · VERIFIED FACULTY
            </p>
            <h1 style={{ margin: '2px 0 6px', fontSize: '24px', fontWeight: 800, color: '#163d31' }}>
              Professor Dashboard
            </h1>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#2d4a3e', marginBottom: '6px' }}>
              Welcome, {displayName}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', fontSize: '13px', color: '#555', alignItems: 'center' }}>
              <span><strong>Department:</strong> {displayDept}</span>
              <span><strong>Designation:</strong> {displayDesig}</span>
              <span><strong>Professor ID:</strong> <code style={{ background: '#e2ebd8', padding: '2px 6px', borderRadius: '4px', fontSize: '12px', color: '#163d31' }}>{displayId}</code></span>
              <span style={{ background: '#dcfce7', color: '#166534', padding: '2px 8px', borderRadius: '4px', fontWeight: 700, fontSize: '11px' }}>
                Status: {displayStatus}
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button id="prof-tab-schedule" className="primary-action" style={{ height: '36px', padding: '0 14px' }} onClick={loadSchedule}>
              <CalendarCheck size={16} /> My Schedule
            </button>
            <button id="prof-tab-pending" className="outline-action" style={{ height: '36px', padding: '0 14px' }} onClick={() => document.getElementById('pending-requests')?.scrollIntoView({ behavior: 'smooth' })}>
              <Clock3 size={16} /> Pending Requests ({pending.length})
            </button>
            <button id="prof-tab-approved" className="outline-action" style={{ height: '36px', padding: '0 14px' }} onClick={() => document.getElementById('upcoming-appointments')?.scrollIntoView({ behavior: 'smooth' })}>
              <CalendarDays size={16} /> Appointments ({upcoming.length})
            </button>
            <button id="refresh-dashboard-btn" className="icon-button" onClick={load} aria-label="Refresh dashboard" title="Refresh">
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="dash-stats">
        <div className="stat-card">
          <span className="stat-number">{total}</span>
          <span className="stat-label">Total requests</span>
        </div>
        <div className="stat-card stat-pending">
          <span className="stat-number">{pending.length}</span>
          <span className="stat-label">Pending review</span>
        </div>
        <div className="stat-card stat-approved">
          <span className="stat-number">{upcoming.length}</span>
          <span className="stat-label">Approved</span>
        </div>
        <div className="stat-card" style={{ borderLeft: '4px solid #ef4444' }}>
          <span className="stat-number">{history.length}</span>
          <span className="stat-label">Closed / History</span>
        </div>
      </div>

      {error && <p className="form-error" style={{ marginBottom: 16 }}>{error}</p>}
      {successMsg && <p className="form-success" style={{ marginBottom: 16 }}>{successMsg}</p>}

      {loading ? (
        <div className="loading-state"><RefreshCw size={16} /><span>Loading requests…</span></div>
      ) : (
        <>
          {/* Pending requests */}
          <section className="appointment-section" id="pending-requests">
            <div className="section-title">
              <Clock3 size={18} />
              <h2>Pending Student Requests</h2>
              <span>{pending.length}</span>
            </div>
            {pending.length === 0 ? (
              <div className="quiet-empty"><Check size={18} /><span>No pending requests. You're all caught up!</span></div>
            ) : (
              <div className="request-cards appointment-list">
                {pending.map((item) => (
                  <PendingCard
                    key={item.appointment_id}
                    item={item}
                    onApprove={approve}
                    onOpenReject={setRejectingItem}
                    onOpenReschedule={openReschedule}
                    isBusy={busyId === item.appointment_id}
                    professorName={displayName}
                    department={displayDept}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Upcoming approved */}
          <section className="appointment-section" id="upcoming-appointments">
            <div className="section-title">
              <CalendarCheck size={18} />
              <h2>Upcoming Appointments</h2>
              <span>{upcoming.length}</span>
            </div>
            {upcoming.length === 0 ? (
              <div className="quiet-empty"><Clock3 size={18} /><span>No upcoming appointments.</span></div>
            ) : (
              <div className="appointment-list">
                {upcoming.map((item) => (
                  <article className="appointment-row" key={item.appointment_id} style={{ borderLeft: '4px solid #22c55e' }}>
                    <div className="appointment-date">
                      <strong>{formatDate(item.date)}</strong>
                      <span>{item.start_time} – {item.end_time || '30 mins'}</span>
                    </div>
                    <div className="appointment-person">
                      <strong>{item.student_name || 'Student'}</strong>
                      <div style={{ fontSize: 12, color: '#666' }}>
                        <span>Email: {item.student_email || item.student_id}</span>
                      </div>
                      <span title={item.reason} style={{ fontSize: 13, color: '#444', marginTop: 2, display: 'block' }}>
                        <strong>Purpose:</strong> {item.reason}
                      </span>
                    </div>
                    <StatusPill status={item.status} />
                    {item.calendar_event_id && (
                      <span className="calendar-sync-status" title="Synced to Google Calendar" style={{ marginLeft: '8px' }}>
                        <CalendarDays size={14} style={{ marginRight: '4px', verticalAlign: 'middle', color: '#4CAF50' }} />
                        <small style={{ color: '#4CAF50' }}>Synced</small>
                      </span>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>

          {/* History */}
          {history.length > 0 && (
            <section className="appointment-section">
              <div className="section-title">
                <CalendarCheck size={18} />
                <h2>Closed / Past Appointments</h2>
                <span>{history.length}</span>
              </div>
              <div className="appointment-list">
                {history.map((item) => (
                  <article className="appointment-row" key={item.appointment_id}>
                    <div className="appointment-date">
                      <strong>{formatDate(item.date)}</strong>
                      <span>{item.start_time} – {item.end_time || '30 mins'}</span>
                    </div>
                    <div className="appointment-person">
                      <strong>{item.student_name || 'Student'}</strong>
                      <span title={item.reason} style={{ display: 'block', fontSize: 13 }}>
                        <strong>Purpose:</strong> {item.reason}
                      </span>
                      {item.rejection_reason && (
                        <span style={{ display: 'block', fontSize: 12, color: '#dc2626', marginTop: 2 }}>
                          <strong>Reason:</strong> {item.rejection_reason}
                        </span>
                      )}
                    </div>
                    <StatusPill status={item.status} />
                  </article>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {/* Rejection Dialog Modal */}
      {rejectingItem && (
        <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && setRejectingItem(null)}>
          <div className="appointment-modal" style={{ width: 'min(480px, 100%)' }}>
            <div className="modal-heading">
              <div>
                <p className="eyebrow" style={{ color: '#dc2626' }}>DECISION</p>
                <h2>Reject Appointment</h2>
              </div>
              <button className="icon-button" onClick={() => setRejectingItem(null)}><X size={18} /></button>
            </div>
            <p style={{ fontSize: 13, color: '#555', marginBottom: 12 }}>
              Are you sure you want to reject the appointment request from <strong>{rejectingItem.student_name}</strong> for <strong>{formatDate(rejectingItem.date)} ({rejectingItem.start_time})</strong>?
            </p>
            <label style={{ display: 'block', marginBottom: 16 }}>
              <span style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 4 }}>Reason for rejection (optional, visible to student):</span>
              <textarea
                style={{ width: '100%', minHeight: 70, padding: 8, borderRadius: 6, border: '1px solid #ccc', fontSize: 13 }}
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="e.g. Schedule conflict with department faculty meeting. Please book another slot."
              />
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="outline-action" onClick={() => setRejectingItem(null)}>
                Cancel
              </button>
              <button
                id="confirm-reject-btn"
                className="primary-action"
                style={{ background: '#dc2626', borderColor: '#dc2626' }}
                onClick={confirmReject}
                disabled={busyId === rejectingItem.appointment_id}
              >
                {busyId === rejectingItem.appointment_id ? 'Rejecting...' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reschedule Dialog Modal */}
      {reschedulingItem && (
        <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && setReschedulingItem(null)}>
          <div className="appointment-modal" style={{ width: 'min(480px, 100%)' }}>
            <div className="modal-heading">
              <div>
                <p className="eyebrow" style={{ color: '#0284c7' }}>TIMETABLE</p>
                <h2>Reschedule Appointment</h2>
              </div>
              <button className="icon-button" onClick={() => setReschedulingItem(null)}><X size={18} /></button>
            </div>
            <p style={{ fontSize: 13, color: '#555', marginBottom: 14 }}>
              Select a new date and time for <strong>{reschedulingItem.student_name}</strong>'s appointment:
            </p>
            <label style={{ display: 'block', marginBottom: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 4 }}>New Date:</span>
              <input
                type="date"
                min={new Date(Date.now() + 86400000).toLocaleDateString('en-CA')}
                value={newDate}
                onChange={(e) => onDateChange(e.target.value)}
                style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #ccc' }}
              />
            </label>
            <label style={{ display: 'block', marginBottom: 16 }}>
              <span style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 4 }}>New Available Slot:</span>
              <select
                value={newTime}
                onChange={(e) => setNewTime(e.target.value)}
                style={{ width: '100%', padding: '7px 10px', borderRadius: 6, border: '1px solid #ccc' }}
                disabled={!availableSlots.length}
              >
                {availableSlots.length === 0 ? (
                  <option value="">No slots available on this date</option>
                ) : (
                  availableSlots.map((s) => (
                    <option key={s.start_time} value={s.start_time}>{s.start_time} – {s.end_time}</option>
                  ))
                )}
              </select>
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="outline-action" onClick={() => setReschedulingItem(null)}>
                Cancel
              </button>
              <button
                id="confirm-reschedule-btn"
                className="primary-action"
                onClick={confirmReschedule}
                disabled={!newTime || busyId === reschedulingItem.appointment_id}
              >
                {busyId === reschedulingItem.appointment_id ? 'Rescheduling...' : 'Confirm Reschedule'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manage Schedule Modal */}
      {showSchedule && (
        <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && setShowSchedule(false)}>
          <div className="appointment-modal" style={{ width: 'min(520px, 100%)' }}>
            <div className="modal-heading">
              <div>
                <p className="eyebrow">YOUR AVAILABILITY</p>
                <h2>Manage Weekly Schedule</h2>
              </div>
              <button className="icon-button" onClick={() => setShowSchedule(false)}><X size={18} /></button>
            </div>
            
            <p style={{ fontSize: 13, color: '#666', marginBottom: 12 }}>
              Define the 30-minute consultation window during which students can book appointments with you.
            </p>

            <div style={{ display: 'grid', gap: '8px', maxHeight: '50vh', overflowY: 'auto', marginBottom: '16px' }}>
              {schedule.map((slot, idx) => (
                <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'center', background: '#fafafa', padding: 8, borderRadius: 6 }}>
                  <select
                    style={{ flex: 1, padding: '6px', borderRadius: '4px', border: '1px solid #dfe6dc' }}
                    value={slot.day}
                    onChange={(e) => {
                      const newSched = [...schedule]
                      newSched[idx].day = e.target.value
                      setSchedule(newSched)
                    }}
                  >
                    {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                  <input
                    type="time"
                    style={{ padding: '5px', borderRadius: '4px', border: '1px solid #dfe6dc' }}
                    value={slot.start_time}
                    onChange={(e) => {
                      const newSched = [...schedule]
                      newSched[idx].start_time = e.target.value
                      setSchedule(newSched)
                    }}
                  />
                  <span>to</span>
                  <input
                    type="time"
                    style={{ padding: '5px', borderRadius: '4px', border: '1px solid #dfe6dc' }}
                    value={slot.end_time}
                    onChange={(e) => {
                      const newSched = [...schedule]
                      newSched[idx].end_time = e.target.value
                      setSchedule(newSched)
                    }}
                  />
                  <button
                    className="icon-button"
                    style={{ color: '#a34434' }}
                    onClick={() => setSchedule(schedule.filter((_, i) => i !== idx))}
                    title="Remove slot"
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
            
            <button
              className="outline-action"
              onClick={() => setSchedule([...schedule, { day: 'Monday', start_time: '10:00', end_time: '12:00', status: 'AVAILABLE' }])}
              style={{ marginBottom: '16px' }}
            >
              + Add Available Slot
            </button>

            <button id="save-schedule-submit" className="primary-action" style={{ width: '100%' }} onClick={saveSchedule} disabled={savingSchedule}>
              {savingSchedule ? 'Saving...' : 'Save Schedule'}
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
