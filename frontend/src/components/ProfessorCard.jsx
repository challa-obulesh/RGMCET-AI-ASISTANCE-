import { useEffect, useState } from 'react'
import { CalendarPlus, Clock3, MapPin, Search, UserRound } from 'lucide-react'
import { api } from '../services/api.js'

export default function ProfessorCard({ professor, onBook }) {
  const [schedule, setSchedule] = useState([])
  const [scheduleError, setScheduleError] = useState('')
  useEffect(() => {
    api.schedule(professor.professor_id).then(setSchedule).catch((error) => setScheduleError(error.message))
  }, [professor.professor_id])

  return (
    <article className="professor-card">
      <div className="professor-top"><span className="professor-avatar"><UserRound size={20} /></span>{professor.is_demo && <span className="demo-label">DEMO DATA</span>}</div>
      <h2>{professor.name}</h2>
      <p className="professor-dept">{professor.department} <span>·</span> {professor.designation}</p>
      <div className="professor-detail"><MapPin size={15} /><span>{professor.office}{professor.room ? ` · ${professor.room}` : ''}</span></div>
      <div className="schedule-block"><div className="schedule-heading"><Clock3 size={15} /> Weekly schedule</div>
        {scheduleError ? <p className="muted">{scheduleError}</p> : schedule.length ? schedule.map((item) => (
          <div className="schedule-line" key={item.schedule_id || item.day}><span>{item.day}</span><strong>{item.start_time}–{item.end_time}</strong></div>
        )) : <p className="muted">No schedule published</p>}
      </div>
      <button className="outline-action" onClick={() => onBook(professor)}><CalendarPlus size={16} /> Request appointment</button>
    </article>
  )
}

export function ProfessorSearch({ value, onChange }) {
  return <label className="search-field"><Search size={17} /><input value={value} onChange={(event) => onChange(event.target.value)} placeholder="Search professors or departments" /></label>
}