const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

function getToken() {
  try { return localStorage.getItem('rgmcet-token') || '' } catch { return '' }
}

async function request(path, options = {}) {
  const token = getToken()
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.detail || 'The service could not complete that request.')
  return payload
}

export const api = {
  // Chat
  chat: (body) => request('/chat', { method: 'POST', body: JSON.stringify(body) }),

  // Professors
  professors: (query = '') => request(`/professors${query ? `?q=${encodeURIComponent(query)}` : ''}`),
  schedule: (id) => request(`/professors/${encodeURIComponent(id)}/schedule`),
  availability: (id, date) => request(`/professors/${encodeURIComponent(id)}/availability?date=${date}`),

  // Appointments
  createAppointment: (body) => request('/appointments', { method: 'POST', body: JSON.stringify(body) }),
  studentAppointments: (id) => request(`/students/${encodeURIComponent(id)}/appointments`),
  myAppointments: () => request('/appointments'),
  pendingAppointments: () => request('/appointments?status=PENDING_APPROVAL'),
  professorAppointments: (status) => request(`/professor/appointments${status ? `?status=${status}` : ''}`),
  decideAppointment: (id, decision) =>
    request(`/appointments/${encodeURIComponent(id)}/${decision}`, { method: 'POST' }),
  getAppointment: (id) => request(`/appointments/${encodeURIComponent(id)}`),

  // Auth
  register: (body) => request('/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  login: (body) => request('/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  me: () => request('/auth/me'),

  // Health
  health: () => request('/health'),

  // Utils
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path) => request(path, { method: 'DELETE' }),
  updateSchedule: (id, slots) => request(`/professors/${encodeURIComponent(id)}/schedule`, { method: 'PUT', body: JSON.stringify({ slots }) }),
}

export const DEMO_STUDENT_ID = 'demo-student'