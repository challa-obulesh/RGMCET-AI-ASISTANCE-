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
  professorDashboard: () => request('/professor/dashboard'),
  decideAppointment: (id, decision, body = {}) =>
    request(`/appointments/${encodeURIComponent(id)}/${decision}`, {
      method: 'POST',
      body: Object.keys(body).length > 0 ? JSON.stringify(body) : undefined,
    }),
  rejectAppointment: (id, reason) =>
    request(`/appointments/${encodeURIComponent(id)}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  rescheduleAppointment: (id, date, start_time) =>
    request(`/appointments/${encodeURIComponent(id)}/reschedule`, {
      method: 'PATCH',
      body: JSON.stringify({ date, start_time }),
    }),
  getAppointment: (id) => request(`/appointments/${encodeURIComponent(id)}`),

  // Auth
  register: (body) => request('/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  login: (body) => request('/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  me: () => request('/auth/me'),

  // Admin Professor Approvals
  professorApprovals: () => request('/admin/professors/approvals'),
  adminApproveUser: (id) => request(`/admin/professors/${encodeURIComponent(id)}/approve`, { method: 'POST' }),
  adminRejectUser: (id) => request(`/admin/professors/${encodeURIComponent(id)}/reject`, { method: 'POST' }),
  adminSuspendUser: (id) => request(`/admin/professors/${encodeURIComponent(id)}/suspend`, { method: 'POST' }),
  adminReactivateUser: (id) => request(`/admin/professors/${encodeURIComponent(id)}/reactivate`, { method: 'POST' }),

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