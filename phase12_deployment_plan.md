# Phase 12 Deployment Plan — RGMCET AI Campus Assistant

## 1. Executive Summary & Objective
Phase 12 transitions the RGMCET AI Campus Assistant from local development/testing to a fully live, publicly accessible production architecture over HTTPS. This document details the infrastructure selection, secret management, containerization/build strategies, environment variable specifications, security policies, rollback workflows, and the 55-gate visible Google Chrome verification matrix (P01–P55).

---

## 2. Selected Hosting & Cloud Architecture

```
                               ┌───────────────────────────┐
                               │       Public Internet      │
                               └─────────────┬─────────────┘
                                             │ HTTPS
                                             ▼
                               ┌───────────────────────────┐
                               │    Render / Cloud Run     │
                               │  FastAPI + React Monolith │
                               │  (or Vercel + Render)     │
                               │   Public HTTPS Domain     │
                               └─────────────┬─────────────┘
                                             │
                       ┌─────────────────────┼─────────────────────┐
                       │                     │                     │
                       ▼                     ▼                     ▼
             ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
             │  MongoDB Atlas   │  │   Gemini 2.0 /   │  │ Google Calendar  │
             │ Cloud Database   │  │   OpenAI Hosted  │  │ API Integration  │
             │ (M0 Free Cluster)│  │   LLM Provider   │  │   (OAuth 2.0)    │
             └──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Hosting Strategy:
1. **Primary Monolithic Single-Service Production Deployment (Recommended & Free/Low-Cost)**:
   - **Platform**: Render / Railway / Google Cloud Run / Hugging Face Spaces (Docker).
   - **Backend**: Python 3.11/3.12 FastAPI ASGI server (`uvicorn app.web_mvp.main:app --host 0.0.0.0 --port $PORT`).
   - **Frontend**: Pre-compiled Vite production bundle (`frontend/dist`) mounted and served directly by FastAPI at `/` with HTML5 push-state SPA routing.
   - **Advantages**:
     - Single unified HTTPS public domain (eliminates cross-origin CORS latency and SSL handshake delays).
     - Unified logging, health checking (`/api/health`), and zero mixed-content security issues.
     - Fully automated containerized build via `Dockerfile`.
2. **Alternative Decoupled Deployment**:
   - **Frontend**: Vercel / Netlify / Cloudflare Pages (serving `frontend/dist` with `VITE_API_BASE_URL=https://<backend-url>/api`).
   - **Backend**: Render / Railway / Koyeb Web Service.
   - **Database**: MongoDB Atlas M0 Free Tier (persistent cloud replica set).

---

## 3. Production Database Configuration
- **Database Engine**: MongoDB Atlas (Cloud Managed Cluster, AWS/GCP region ap-south-1 Mumbai / Singapore).
- **Fallback Engine**: In-memory demo store activated when `DEMO_MODE=true` or database string is absent.
- **Connection Security**: TLS 1.3 encrypted connection string `mongodb+srv://...` with least-privilege credentials.
- **Connection Timeout**: `serverSelectionTimeoutMS=5000` with graceful error recovery on transient network partition.
- **Collections & Indexes**:
  - `users`: Unique indexes on `user_id`, `email`.
  - `professors`: Unique index on `professor_id`, text index on `name`, `aliases`.
  - `professor_schedules`: Compound index on `(professor_id, day)`.
  - `appointments`: Unique compound index on `(professor_id, date, start_time)` ensuring zero double-booking.
  - `audit_logs`: Timestamp-indexed append-only compliance journal.

---

## 4. Environment Variables & Secret Management Specification

### Server-Side Environment Variables (Confidential — Stored in Cloud Secret Manager / Render Secrets):
| Variable Name | Description | Example / Required Format |
| :--- | :--- | :--- |
| `APP_ENV` | Runtime environment flag | `production` |
| `DEMO_MODE` | Toggle database vs in-memory fallback | `false` (for live DB) or `true` |
| `PORT` | Dynamic web port assigned by cloud host | Assigned dynamically by provider (defaults to `8000`) |
| `MONGODB_URI` | MongoDB Atlas TLS connection URI | `mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority` |
| `DATABASE_NAME` | Database catalog name | `rgmcet_ai_assistant` |
| `JWT_SECRET` | 256-bit cryptographically secure signing key | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_EXPIRE_MINUTES` | Access token lifespan | `120` |
| `LLM_PROVIDER` | Active LLM driver | `gemini` or `openai` |
| `GEMINI_API_KEY` | Google AI Studio API Secret Key | Private key |
| `GEMINI_MODEL` | Target Gemini model identifier | `gemini-2.0-flash` |
| `OPENAI_API_KEY` | OpenAI Secret API Key (if selected) | Private key |
| `OPENAI_MODEL` | Target OpenAI model identifier | `gpt-4o-mini` |
| `CORS_ORIGINS` | Permitted cross-origin origins | `https://rgmcet-ai-campus-assistant.onrender.com` |
| `GOOGLE_CALENDAR_ENABLED` | Toggle live Google Calendar sync | `false` (demo fallback) or `true` |
| `GOOGLE_CLIENT_ID` | OAuth2 Client ID | `client-id.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | OAuth2 Client Secret | Private key |
| `GOOGLE_REFRESH_TOKEN` | Long-lived authorized refresh token | Private token |

### Build-Time Frontend Variables (Public):
| Variable Name | Description | Production Value |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Root relative or public absolute API path | `/api` (for unified host) |

> [!CAUTION]
> **Secret Hygiene Rules**:
> - Never commit `.env` or credential files to Git.
> - Secrets must never be prefixed with `VITE_` or embedded into JavaScript bundles.
> - Server-side secrets are injected strictly via host environment variables.

---

## 5. Build, Packaging & Containerization Strategy

### A. Containerized Docker Build (`Dockerfile`)
```dockerfile
FROM python:3.11-slim as backend
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends curl nodejs npm && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

COPY . .
RUN cd frontend && npm run build

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.web_mvp.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

### B. Health Checks & Probes
- **Readiness / Health Endpoint**: `GET /api/health`
  - Returns HTTP 200:
    ```json
    {
      "status": "ok",
      "demo_mode": false,
      "database": "connected",
      "llm_provider": "gemini",
      "version": "0.3.0"
    }
    ```

---

## 6. Security, CORS & Network Policies
1. **HTTPS Everywhere**: Strict Transport Security and redirect to HTTPS on cloud ingress.
2. **Security Headers**:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy: strict-origin-when-cross-origin`
3. **CORS Policy**: Configured to exact production origin (`allow_credentials=True`, specific HTTPS methods allowed).
4. **Rate Limiting & Safety**: Non-blocking in-memory rate limiting and `max_length=500` validation on all input prompts.

---

## 7. Rollback & Disaster Recovery Strategy
1. **Git Commit Hash Versioning**: Every deployment is directly traceable to an immutable Git SHA.
2. **Instant Rollback**: If a production deployment fails health checks or visible verification, rollback to previous release via provider dashboard / Git tag within < 60 seconds.
3. **Database Safeguards**: Automated Atlas daily snapshots; schema migrations are additive and backward-compatible.

---

## 8. Final Visible Google Chrome Production Verification Matrix (P01–P55)

| Code | Scenario | Verification Method |
| :--- | :--- | :--- |
| **P01** | Public Homepage Loads | Visibly open public HTTPS URL in Chrome |
| **P02** | HTTPS Active & Valid Cert | Chrome URL bar shows valid SSL lock icon |
| **P03** | No Mixed-Content Errors | Console inspection for insecure HTTP assets |
| **P04** | Zero Critical Console Errors | DevTools console monitoring |
| **P05** | No Unexpected 4xx/5xx Errors | Network panel monitoring |
| **P06** | Student Registration & Login | Full auth cycle via UI |
| **P07** | Student Dashboard Navigation | View schedule and appointment history |
| **P08** | Student AI Chat Interface | Open chat modal / page |
| **P09** | English AI Query & Response | Ask CSE department faculty questions |
| **P10** | Telugu Language AI Query | Ask in Telugu script |
| **P11** | Roman Telugu AI Query | Ask in Romanized Telugu |
| **P12** | RGMCET Knowledge Grounding | Verify answers cite official RGMCET records |
| **P13** | RAG Source Attribution | Source metadata cards displayed |
| **P14** | Professor Registration Workflow | Register professor $\to$ verify status `PENDING` |
| **P15** | Professor Login Enforcement | Blocked before approval, permitted after |
| **P16** | Professor Dashboard | View stats and appointment sections |
| **P17** | Professor Availability / Schedule | View & edit working slots |
| **P18** | Student Creates Appointment | Select professor, date, time, purpose |
| **P19** | Appointment State Initialized | Status = `PENDING_APPROVAL` |
| **P20** | Professor Pending Queue | View in `#pending-requests` |
| **P21** | Professor Approves Appointment | Click `[Approve]` $\to$ status becomes `APPROVED` |
| **P22** | Student Verified Status | Student view updates to `APPROVED` |
| **P23** | Professor Rejects Appointment | Click `[Reject]` $\to$ status becomes `REJECTED` |
| **P24** | Student Rejection Notification | Status = `REJECTED` visible |
| **P25** | Student Appointment Cancellation | Student cancels appointment $\to$ `CANCELLED` |
| **P26** | Appointment Rescheduling | Reschedule flow if requested |
| **P27** | Google Calendar Sync | Verify sync badge or fallback |
| **P28** | Admin Login | Authenticate with administrator credentials |
| **P29** | Admin Dashboard Overview | Total users, knowledge records, AI metrics |
| **P30** | Admin Users Tab | User table loaded with status badges |
| **P31** | Admin Approves/Rejects Professor | Status action buttons executed |
| **P32** | Admin Appointments Tab | Complete appointment ledger loaded |
| **P33** | Admin Appointment Filtering | Filter by status pill |
| **P34** | Admin Appointment Override | Execute override with audit reason |
| **P35** | Admin Audit Logs Tab | View audit events |
| **P36** | Admin AI Analytics Tab | Intent and language distribution |
| **P37** | Admin Agent Status Tab | Inspect available tools and workflow capabilities |
| **P38** | Admin System Health Tab | Real-time health metrics |
| **P39** | Knowledge Record Management | CRUD, verify, unverify, archive records |
| **P40** | RAG Status & Indexing | View index counts and trigger re-index |
| **P41** | RAG Query Preview | Execute live grounded query preview |
| **P42** | Unauthorized Student Access Blocked | Student accessing `/api/admin/*` gets HTTP 403 |
| **P43** | Unauthorized Professor Access Blocked | Professor accessing `/api/admin/*` gets HTTP 403 |
| **P44** | Appointment Ownership Isolation | Cross-user appointment mutation blocked |
| **P45** | Desktop Viewport Layout | 1366x768 verification, zero overflow |
| **P46** | Mobile Viewport Layout | 390x844 responsive navigation & touch targets |
| **P47** | Session Persistence | Page reload maintains logged-in state |
| **P48** | Logout Workflow | Clear token and redirect |
| **P49** | Re-login Workflow | Re-authenticate smoothly |
| **P50** | Public Backend Health Endpoint | `https://<domain>/api/health` returns HTTP 200 |
| **P51** | Production Data Persistence | Verify created records survive refresh/restart |
| **P52** | LLM Failure Graceful Fallback | Error handling returns helpful fallback |
| **P53** | Zero Exposed Secrets in Browser | DevTools audit shows no secret leakage |
| **P54** | Zero Localhost Network Requests | Network panel shows 100% public domain traffic |
| **P55** | HTTPS-Only Production Traffic | All communications encrypted |
