# RGMCET AI Campus Assistant - Phase 10 Admin Plan

## 1. Existing Architecture
- **Backend:** FastAPI, providing modular APIs (auth, chat, appointments, professors).
- **Database:** store.py acts as a lightweight repository layer connecting to MongoDB or falling back to in-memory for demo modes.
- **Frontend:** React + Vite (App.jsx), custom Context-based auth, standard routing based on state (page).
- **Knowledge/RAG:** VectorStore (JSON-backed embedding store) loaded at startup. Embeddings generated via Google's text-embedding-004 (with a local fallback). RAG logic resides in knowledge.py and embeddings.py.
- **Analytics/Logging:** Currently relies entirely on standard python logging. Chat sessions are stored but not aggregated.

## 2. Existing Authorization Model
- JWT-based authentication in auth.py. 
- role is embedded in the JWT payload (currently supports student and professor).
- Frontend routing guards student and professor pages based on user.role.

## 3. Admin Features to Add
1. **Admin Role Integration:** Expand auth_schemas.py to allow admin role. Add require_admin dependency to backend.
2. **Admin Dashboard (Frontend):** New /admin route with overview metrics, knowledge management, analytics, and audit logs.
3. **Knowledge Management API:** CRUD for knowledge records, with verified flag management.
4. **RAG Re-indexing API:** Endpoint to force recalculation of embeddings for knowledge records and update VectorStore.
5. **System Health API:** Basic status reporting for DB, LLM, etc.
6. **Analytics Endpoints:** Aggregate metrics for appointments, chats, and users.
7. **Audit Logging:** New audit_logs collection/store to track sensitive admin actions.

## 4. API Changes
We will introduce the following routes under a new admin.py router:
- GET /api/admin/overview
- GET /api/admin/knowledge, POST, PATCH, DELETE
- POST /api/admin/knowledge/{id}/verify, unverify
- POST /api/admin/knowledge/reindex, GET .../status
- GET /api/admin/faculty, departments, facilities
- GET /api/admin/analytics/appointments, chat, agent
- GET /api/admin/users
- GET /api/admin/health
- GET /api/admin/audit-logs

## 5. Frontend Changes
- Update App.jsx to support admin role and restrict access.
- Add Sidebar navigation items for Admin.
- Create AdminDashboard.jsx (Overview + Analytics).
- Create AdminKnowledge.jsx (CRUD table + Re-index trigger + Preview panel).

## 6. Security Requirements
- require_admin dependency will validate JWT and ensure role == 'admin'.
- Passwords and secrets will NEVER be returned in any admin payload (enforced via Pydantic response models).
- Destructive actions (delete/archive) will require confirmation on the frontend.
- Strict isolation: student and professor roles must receive 403 Forbidden.

## 7. Test Plan
- Unit tests for authentication edge cases (Admin isolation).
- Unit tests for all /api/admin/* endpoints.
- Ensure 144 existing tests still pass.

## 8. Browser Verification Plan
- Extend run_portable_verification.py to include R04 to R26 scenarios.
- Verify Admin login, dashboard load, knowledge search/edit, re-indexing, and query preview via Playwright (headless=False).
- Verify access denial for non-admins.

## 9. Rollback Risks
- Breaking the RAG retrieval if re-indexing fails. Mitigation: Re-indexing will write to a temporary state and only swap the store on success.
- Accidentally breaking student/professor routing. Mitigation: Keep existing routing untouched; only add the new admin case.

## 10. Acceptance Criteria
- Fully functional Admin Dashboard.
- Knowledge CRUD and Re-indexing working.
- No regression in Phases 1-9.
- 100% visible Chrome verification success.
