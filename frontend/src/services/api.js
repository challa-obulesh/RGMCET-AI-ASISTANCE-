const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.detail || 'The service could not complete that request.')
  return payload
}

export const api = {
  chat: (body) => request('/chat', { method: 'POST', body: JSON.stringify(body) }),
  professors: (query = '') => request(`/professors${query ? `?q=${encodeURIComponent(query)}` : ''}`),
  schedule: (id) => request(`/professors/${encodeURIComponent(id)}/schedule`),
  availability: (id, date) => request(`/professors/${encodeURIComponent(id)}/availability?date=${date}`),
  createAppointment: (body) => request('/appointments', { method: 'POST', body: JSON.stringify(body) }),
  studentAppointments: (id) => request(`/students/${encodeURIComponent(id)}/appointments`),
  pendingAppointments: () => request('/appointments?status=PENDING_APPROVAL'),
  decideAppointment: (id, decision) => request(`/appointments/${encodeURIComponent(id)}/${decision}`, { method: 'POST' }),
}

export const DEMO_STUDENT_ID = 'demo-student'