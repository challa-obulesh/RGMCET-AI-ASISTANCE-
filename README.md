# RGMCET AI Campus Assistant

Phase 1 is a web-only campus assistant for student enquiries, professor schedules, and appointment requests. Telegram, WhatsApp, and Google Calendar integration code has been removed from this project scope.

## Architecture

```text
React + Vite web client
        |
        v
FastAPI routes (app.web_mvp.api)
        |
        v
Agent classification -> verified services -> MongoDB / knowledge JSON
```

The agent classifies and extracts intent. Services verify professor records, schedules, appointment conflicts, and campus knowledge before returning a response. The agent never accesses MongoDB directly. Web routes are transport adapters; the same services can later be called by other channels.

## Features

- Responsive RGMCET-branded chat UI with recent chat labels, loading/error states, keyboard submission, and English/Telugu/Roman Telugu intent detection.
- Professor directory, searchable profiles, published weekly schedules, and date-specific 30-minute availability.
- Appointment requests are checked against schedule and existing pending/approved requests, then created as `PENDING_APPROVAL`.
- Basic demo approval/rejection view and student appointment list.
- Optional MongoDB persistence through Motor. Without MongoDB, `DEMO_MODE=true` uses an in-memory store seeded only with clearly labeled demo professor/schedule data.
- Optional OpenAI-compatible hosted intent classification. The local parser is used when credentials are absent or the provider fails; the hosted model is never a source of campus facts or appointment decisions.
- College facts are loaded from structured JSON and explicitly marked unverified until verified content is supplied.

## Stack

- Backend: Python, FastAPI, Pydantic, Uvicorn, Motor, python-dotenv, tzdata
- Frontend: React, Vite, Tailwind CSS, lucide-react
- Database: MongoDB
- Timezone: `Asia/Kolkata`

## Structure

```text
app/web_mvp/             Web-only FastAPI app, routes, services, store, schemas
app/web_intents.py       Structured local intent detection
frontend/                React + Vite application
data/rgmcet_knowledge/   College, department, facility, and timing JSON
data/demo_*.json         Explicitly labeled demo professor and schedule records
scripts/seed_web_data.py Imports demo JSON records into MongoDB
tests/test_web_*.py      Web-agent and API tests
```

## Setup

### Backend

Use Python 3.11 or newer. In PowerShell from the repository root:

```powershell
Copy-Item .env.example .env
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.web_mvp.main:app --reload --port 8000
```

The API starts in in-memory demo mode by default, so MongoDB and an LLM key are optional for local exploration. Demo appointments disappear when the process restarts.

### MongoDB

Set `MONGODB_URI` and `DATABASE_NAME` in `.env`. The app creates indexes at startup. To import the editable demo professor and schedule JSON into the configured database:

```powershell
python scripts/seed_web_data.py
```

Replace `data/demo_professors.json`, `data/demo_professor_schedules.json`, and the knowledge JSON with verified RGMCET records before using this with students. Remove `is_demo` and `DEMO` labels only for records that have been verified.

### Frontend

Install Node.js 20 or newer, then from `frontend/`:

```powershell
npm install
npm run dev
```

The development server is normally at `http://localhost:5173`. Set `VITE_API_BASE_URL` if the FastAPI server is not at `http://localhost:8000/api`.

## Environment

| Variable | Purpose | Default |
|---|---|---|
| `MONGODB_URI` | MongoDB connection string; blank selects demo memory store | blank |
| `DATABASE_NAME` | MongoDB database name | `rgmcet_ai` |
| `DEMO_MODE` | Enables clearly marked in-memory demo records when MongoDB is absent | `true` |
| `LLM_API_KEY` | Hosted OpenAI-compatible API key, backend only | blank |
| `LLM_MODEL` | Hosted model name | `gpt-4o-mini` |
| `LLM_BASE_URL` | Chat-completions-compatible endpoint | OpenAI endpoint |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173` |
| `VITE_API_BASE_URL` | Frontend API base URL | `http://localhost:8000/api` |

Never put an LLM secret in a `VITE_` variable. The approval actions and demo student identity are intentionally unauthenticated for local MVP testing; do not expose this service publicly until authentication and role authorization are added.

## Authentication and Roles

Authentication and authorization are **NOT IMPLEMENTED** and are required before public deployment. The minimum role boundary should be:

- Student: chat, search/view professors, request appointments, and view only their own appointments.
- Professor: view their pending requests and schedule, then approve or reject their requests.
- Admin: manage verified RGMCET knowledge, professor profiles, and schedules.

Current demo routes do not enforce these boundaries; the pending queue and decision endpoints are available to any caller.

## API

- `GET /api/health`
- `POST /api/chat`
- `GET /api/professors`
- `GET /api/professors/search?q=...`
- `GET /api/professors/{professor_id}`
- `GET /api/professors/{professor_id}/schedule`
- `GET /api/professors/{professor_id}/availability?date=YYYY-MM-DD`
- `POST /api/appointments`
- `GET /api/appointments?status=PENDING_APPROVAL`
- `GET /api/appointments/{appointment_id}`
- `GET /api/students/{student_id}/appointments`
- `POST /api/appointments/{appointment_id}/approve`
- `POST /api/appointments/{appointment_id}/reject`
- `POST /api/appointments/{appointment_id}/cancel`

Appointment requests are never reported as confirmed on creation. They remain `PENDING_APPROVAL` until an explicit approval action. Slot validation checks the published schedule and overlapping active requests; active-slot claims use a MongoDB unique partial index and an atomic in-memory demo-store insert.

## Tests

```powershell
python -m pytest tests/test_web_intents.py tests/test_web_api.py -q
```

The web tests cover the required multilingual intent prompt matrix, hosted LLM fallback, demo professor search/details/schedules, availability, appointment validation/conflicts and state transitions, chat sessions, malformed input, and CORS.

## Limitations

- No verified RGMCET facts or real professor data are included. Knowledge JSON currently returns explicit "not verified" responses.
- Demo data and demo appointment state are not durable unless MongoDB is configured and records imported.
- Demo authentication is not secure and approval routes need role-based authorization before deployment.
- The optional LLM classifies intent only; multilingual response generation is limited and can fall back to short local templates.
- Atomic concurrency is covered in the in-memory test suite, but the MongoDB unique index has not been exercised because MongoDB is unreachable in this environment. Existing active appointments are migrated to active slot claims at startup.
- Authentication and role authorization are NOT IMPLEMENTED and are required before public deployment.
- No calendar synchronization, notifications, RAG, maps, voice features, Telegram, or WhatsApp integrations are included in this MVP.

## Roadmap

- Phase 1: Web chatbot, professor interaction, schedules, appointment workflow.
- Phase 2: Retrieval-augmented answers over verified RGMCET documents.
- Phase 3: Telegram and WhatsApp channel adapters reusing the same services.
- Phase 4: Calendar integration and notifications.