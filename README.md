# RGMCET AI Campus Assistant

[![CI Test Pipeline](https://github.com/challa-obulesh/RGMCET-AI-ASISTANCE-/actions/workflows/ci.yml/badge.svg)](https://github.com/challa-obulesh/RGMCET-AI-ASISTANCE-/actions)
[![Production Status](https://img.shields.io/badge/Render-Live%20Production-success?logo=render&logoColor=white)](https://rgmcet-ai-campus-assistant.onrender.com)
[![Release Version](https://img.shields.io/badge/Release-v0.3.0-blue.svg)](https://github.com/challa-obulesh/RGMCET-AI-ASISTANCE-/releases)
[![Tests Passing](https://img.shields.io/badge/Tests-250%2F250%20Passing-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite%206-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Database](https://img.shields.io/badge/Database-MongoDB%20Atlas-47A248.svg?logo=mongodb&logoColor=white)](https://www.mongodb.com/atlas)
[![AI Grounding](https://img.shields.io/badge/LLM-Gemini%202.0%20Flash-orange.svg?logo=google-gemini&logoColor=white)](https://deepmind.google/technologies/gemini/)

> An intelligent, production-ready campus inquiry and appointment management platform tailored for Rajeev Gandhi Memorial College of Engineering and Technology (RGMCET). Built with a FastAPI backend, React + Vite single-page frontend, semantic RAG knowledge grounding, and multi-role workflows for Students, Professors, and Administrators.

---

## 📑 Table of Contents

- [🌐 Live Demo & Deployment](#-live-demo--deployment)
- [📋 Project Overview](#-project-overview)
- [✨ Key Features](#-key-features)
- [🏛️ System Architecture](#️-system-architecture)
- [🧠 AI & RAG Architecture](#-ai--rag-architecture)
- [🔄 User & Appointment Workflows](#-user--appointment-workflows)
- [🔒 Authentication & Security](#-authentication--security)
- [🛠️ Technology Stack](#️-technology-stack)
- [📁 Project Structure](#-project-structure)
- [🔑 Environment Variables](#-environment-variables)
- [💻 Local Development Setup](#-local-development-setup)
- [🚀 Production Deployment](#-production-deployment)
- [🧪 Testing & Verification Status](#-testing--verification-status)
- [🛡️ Security Best Practices & Data Privacy Hardening](#️-security-best-practices--data-privacy-hardening)
- [🌿 Version Control, Branching & Release Management](#-version-control-branching--release-management)
- [🔮 Future Improvements](#-future-improvements)
- [👨‍💻 Project Information & License](#-project-information)

---

## 🌐 Live Demo & Deployment

The application is deployed live in production on **Render** with cloud persistence on **MongoDB Atlas**:

🔗 **Production URL**: [https://rgmcet-ai-campus-assistant.onrender.com](https://rgmcet-ai-campus-assistant.onrender.com/)

> [!NOTE]
> **Free Tier Cold Start Notice**: The production service is hosted on Render's free tier. If the instance has been inactive, the initial request may spin up the container and take approximately 30–60 seconds for a cold start. Subsequent requests execute instantly.

* **Primary GitHub Branch**: `main` (Production deployment branch)
* **Milestone & Release Tag**: `v0.3.0`
* **Platform Architecture**: Single-origin web application (FastAPI serving compiled React/Vite SPA and REST API)

---

## 📋 Project Overview

### Problem Statement
College campuses host a high volume of recurring administrative inquiries regarding departmental structures, faculty contacts, academic programs, facilities, and visiting schedules. Students frequently face friction when seeking official, verified information or attempting to book time with professors whose availability varies across teaching timetables. Traditional bulletin boards and ungrounded messaging bots often present outdated details, lack accountability, or risk generating AI hallucinations.

### The Solution
The **RGMCET AI Campus Assistant** is a dedicated, website-only platform that unites:
1. **Grounded AI Campus Enquiry**: An intelligent chat assistant strictly anchored to official RGMCET institutional data, offering multilingual support (English, Telugu, and Roman Telugu) with verifiable source links and a deterministic fallback layer.
2. **Professor Directory & Availability Booking**: A structured appointment scheduling system enabling students to view verified 30-minute faculty availability slots and book consultations.
3. **Role-Based Portals**: Dedicated workspaces for Students, Professors (with admin verification workflows), and College Administrators with full governance, auditing, and RAG index control.

---

## ✨ Key Features

### 🤖 Grounded AI Campus Enquiry
* **Official Institutional Grounding**: Pre-indexed campus data covering departments, B.Tech/M.Tech programs, HODs, faculty rosters, campus timings, and college facilities.
* **Semantic RAG Pipeline**: Combines vector embeddings and lexical intent detection to retrieve relevant institutional records before response generation.
* **Hallucination Guardrails**: Prompts restrict the LLM to verified knowledge. If specific details (e.g., private cabin room numbers or unverified schedules) are not verified, the system safely declines rather than inventing facts.
* **Multilingual Interaction**: Native understanding and conversational fluency in **English**, **Telugu (తెలుగు)**, and **Roman Telugu** (e.g., *"CSE Data Science HOD evaru?"*).
* **Source Attribution**: Transparent responses with verifiable citations and source links to official RGMCET pages.
* **Resilient AI Fallback**: If external LLM API endpoints experience rate limits or network latency, the platform automatically switches to a deterministic pattern/keyword intent engine without breaking the user experience.

### 🎓 Student Features
* **Authentication & Dashboard**: Secure registration, JWT-authenticated login, and personal activity overview.
* **AI Chat Assistant**: Real-time conversational interface with persistent chat history.
* **Faculty Directory**: Browse faculty by department, view designations, qualifications, and profile details.
* **Appointment Scheduling**: Browse published weekly availability and request 30-minute consultation slots.
* **Appointment Tracking**: Live lifecycle monitoring (`PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `CANCELLED`), cancellation, and slot release for rebooking.

### 👨‍🏫 Professor Features
* **Regulated Onboarding**: Professor registration enters a `PENDING_APPROVAL` queue; accounts cannot log in until verified and activated by an Administrator.
* **Dedicated Professor Dashboard**: High-level metrics showing pending appointment requests, approved meetings, and schedules.
* **Queue Management**: Review pending student consultation requests with one-click **Approve**, **Reject** (with optional feedback), or **Cancel** actions.
* **Schedule & Availability**: Manage weekly availability slots and synchronize student booking states.
* **Calendar Abstraction**: Built-in service abstraction supporting external calendar synchronization (Google Calendar OAuth 2.0 integration with verified fallback).

### 🛡️ Administrator Features
* **Overview & System Metrics**: High-level dashboard tracking user signups, total appointments, active faculty, and system status.
* **Knowledge Management**: Full CRUD operations on campus records (Campus, Department, Facility, Faculty) with verification flags and archiving.
* **RAG Diagnostics & Index Management**: Real-time vector store statistics, on-demand reindexing, and semantic query preview for administrators.
* **Faculty, Department & Facility Views**: Centralized catalog management for all institutional structures.
* **User Management & Approval Workflow**: Approve or reject newly registered professor accounts, modify roles, and toggle user active states.
* **Appointment Governance**: Complete oversight across all student-faculty bookings, status filtering, and administrative overrides.
* **AI Analytics**: Categorized breakdowns of user queries, intent distributions, multilingual traffic shares, and confidence scores.
* **Agent Diagnostics**: Registry inspection of active agent tools and multi-step reasoning traces.
* **Audit Logs**: Immutable audit log recording all administrative overrides, user state changes, and knowledge updates.
* **System Health Monitor**: Live checks verifying backend API, MongoDB Atlas database connectivity, and LLM provider availability.

---

## 🏛️ System Architecture

The following schematics illustrate the complete end-to-end architecture of the **RGMCET AI Campus Assistant**, covering all tiers from user personas down to persistence and external cloud services.

### 1. Interactive Architecture Diagram

```mermaid
flowchart TD
    subgraph Users ["1. User Personas & Portals"]
        StudentRole["Student User"]
        ProfRole["Professor User"]
        AdminRole["Administrator User"]
    end

    subgraph ClientTier ["2. Frontend Web Application (React 18 + Vite)"]
        WebUI["Responsive Single Page App (SPA)"]
        AuthContext["Auth Context & JWT Token Storage"]
        APIService["Axios API Client Layer"]
    end

    subgraph SecurityTier ["3. Gateway & Security Layer (FastAPI)"]
        SecHeaders["Security Headers Middleware"]
        CORSMid["CORS Protection Middleware"]
        AuthMid["JWT Auth & Role-Based Access Control"]
        FastAPIRoutes["FastAPI REST Endpoints (/api/*)"]
    end

    subgraph OrchestrationTier ["4. Core Engine & AI Orchestrator"]
        AgentEngine["AI Agent Orchestrator"]
        RAGModule["Semantic RAG Retrieval Engine"]
        PrivacyGateway["Privacy Gateway (PII & Secret Sanitizer)"]
        AppointmentService["Appointment & Booking Service"]
        CalendarService["Calendar Service Abstraction"]
    end

    subgraph DataTier ["5. Persistence & Knowledge Base"]
        MongoAtlas[("MongoDB Atlas Cloud Database")]
        VectorStore[("Pre-Computed Semantic Vector Index")]
        OfficialKnowledge[("Verified RGMCET Knowledge Base")]
    end

    subgraph ExternalTier ["6. External Cloud & AI Integrations"]
        GeminiLLM["Google Gemini 2.0 Flash API"]
        GoogleCalAPI["Google Calendar API (OAuth 2.0)"]
    end

    StudentRole --> WebUI
    ProfRole --> WebUI
    AdminRole --> WebUI

    WebUI --> AuthContext
    WebUI --> APIService
    APIService --> SecHeaders
    SecHeaders --> CORSMid
    CORSMid --> AuthMid
    AuthMid --> FastAPIRoutes

    FastAPIRoutes --> AgentEngine
    FastAPIRoutes --> AppointmentService

    AgentEngine --> RAGModule
    AgentEngine --> PrivacyGateway
    PrivacyGateway --> GeminiLLM

    RAGModule --> VectorStore
    RAGModule --> OfficialKnowledge

    AppointmentService --> MongoAtlas
    AppointmentService --> CalendarService
    CalendarService -.-> GoogleCalAPI
```

### 2. Complete Architectural Schematic

```
+====================================================================================================+
|                                    RGMCET AI CAMPUS ASSISTANT                                      |
|                                 END-TO-END SYSTEM ARCHITECTURE                                     |
+====================================================================================================+
|                                                                                                    |
|  [ 1. USER PERSONAS & ACCESS ROLES ]                                                               |
|  +--------------------+        +--------------------+        +--------------------+                |
|  |    Student Portal  |        |  Professor Portal  |        |  Admin Workspace   |                |
|  | (Chat, Book, Track)|        | (Approve, Schedule)|        | (RAG, Users, Audit)|                |
|  +---------+----------+        +---------+----------+        +---------+----------+                |
|            |                             |                             |                           |
|            +-----------------------------+-----------------------------+                           |
|                                          | HTTPS / REST (Port 443 / 8000)                          |
|                                          v                                                         |
|  [ 2. CLIENT WEB APPLICATION TIER - React 18 + Vite SPA ]                                          |
|  +--------------------------------------------------------------------------------+                |
|  | - Single Page App (SPA) mounted via FastAPI static file handler                |                |
|  | - Responsive UI: Tailwind CSS Design System + Lucide Icons                      |                |
|  | - State Management: AuthContext (JWT Storage & Role Routing)                   |                |
|  | - Error Boundary: Component-level crash isolation and graceful fallback        |                |
|  +---------------------------------------+----------------------------------------+                |
|                                          | REST API Payloads (Bearer Token Authorization)          |
|                                          v                                                         |
|  [ 3. API GATEWAY & SECURITY TIER - FastAPI (Python 3.11) ]                                        |
|  +--------------------------------------------------------------------------------+                |
|  | - Security Headers: X-Content-Type-Options: nosniff | X-Frame-Options: DENY    |                |
|  | - CORS Middleware: Restricts access to authorized domains & localhost         |                |
|  | - Stateless JWT Authentication & Role-Based Access Control (RBAC dependencies) |                |
|  | - REST Routers: /api/auth | /api/chat | /api/professors | /api/appointments     |                |
|  | - Unhandled Exception Isolation: Generic 500 error preventing stack trace leaks |                |
|  +-------------------+------------------------------------+-----------------------+                |
|                      |                                    |                                        |
|                      v                                    v                                        |
|  [ 4. AI ORCHESTRATION ENGINE ]             [ 5. APPOINTMENT & CALENDAR ENGINE ]                   |
|  +-----------------------------------+      +------------------------------------+                 |
|  | - Multi-Turn AI Agent Loop        |      | - Appointment Lifecycle State Mach |                 |
|  | - Intent Classifier (Multilingual)|      |   (PENDING -> APPROVED / REJECTED) |                 |
|  | - Semantic RAG Retrieval          |      | - 30-min Slot Validation & Locking |                 |
|  | - Deterministic Rule Fallback     |      | - Calendar Service Abstraction     |                 |
|  +-------------------+---------------+      +------------------+-----------------+                 |
|                      |                                         |                                   |
|                      v Outbound Payload                        v Async Motor Driver                |
|  [ 6. CENTRAL PRIVACY GATEWAY ]                                |                                   |
|  +-----------------------------------+                         |                                   |
|  | - Outbound Sanitizer & Redactor   |                         |                                   |
|  | - Strips Emails, Phones, JWTs     |                         |                                   |
|  | - Aborts on Serialization Failure |                         |                                   |
|  +-------------------+---------------+                         |                                   |
|                      |                                         |                                   |
|  ====================+=========================================+=================================  |
|  [ 7. PERSISTENCE & EXTERNAL CLOUD INTEGRATIONS ]                                                  |
|                                                                                                    |
|  +-----------------------+     +-----------------------+     +-----------------------+             |
|  |  Google Gemini 2.0    |     |  Verified Knowledge   |     |  MongoDB Atlas        |             |
|  |  Flash (LLM API)      |     |  & Vector Store       |     |  (Cloud Database)     |             |
|  | Grounded Generation   |     | - Pre-computed Vectors|     | - Users & Credentials |             |
|  | Multilingual Telugu   |     | - Department Catalog  |     | - Appointments & Slots|             |
|  | Zero-Hallucination    |     | - Official Facilities |     | - Audit Logs & Chats  |             |
|  +-----------------------+     +-----------------------+     +-----------------------+             |
+====================================================================================================+
```

### 3. Layer-by-Layer Architectural Breakdown

| Architectural Layer | Core Technologies | Primary Responsibilities |
| :--- | :--- | :--- |
| **Presentation Tier** | React 18, Vite 6, Tailwind CSS, Lucide | Role-tailored dashboards for Students, Professors, and Admins; real-time conversational chat UI with citation links; faculty appointment booking and schedule tracking. |
| **Security & Gateway Tier** | FastAPI, `python-jose`, `passlib[bcrypt]`, Starlette | HTTP security headers (`nosniff`, `DENY`), strict CORS whitelist, stateless JWT validation, RBAC route dependencies, and non-leaking global error handling. |
| **AI Orchestration & RAG Tier** | Python 3.11, Vector Embeddings, ReAct Agent | Multilingual intent detection (English, Telugu, Roman Telugu), semantic retrieval over institutional documents, deterministic fallback engine, and tool execution. |
| **Data Privacy Gateway** | Custom Regex Tokenizer & Sanitizer | Automated stripping of emails, phone numbers, API keys, database URIs, and JWT credentials before any external model dispatch. |
| **Persistence Tier** | MongoDB Atlas (Motor Async Driver), JSON Vector Index | Cloud persistence of users, appointments, audit logs, and pre-indexed cosine vector representations of official campus knowledge. |
| **External Integrations** | Google Gemini API (`gemini-2.0-flash`), Google Calendar API | Grounded LLM conversational generation, source-attributed responses, and OAuth 2.0 calendar synchronization. |

---

## 🧠 AI & RAG Architecture

```
User Message (English / Telugu / Roman Telugu)
   │
   ▼
1. Pre-Processing & Language / Intent Classification
   │
   ▼
2. Semantic Retrieval (RAG)
   ├── Query Vectorization (Embeddings)
   ├── Cosine Similarity Match against Verified RGMCET Knowledge
   └── Context Assembly with Source Attribution Links
   │
   ▼
3. Reasoning & Tool Calling (ReAct Loop)
   ├── `search_knowledge`      -> Institutional data lookup
   ├── `search_professor`      -> Faculty directory lookup
   ├── `check_availability`    -> Timetable slot verification
   └── `create_appointment`    -> Guarded booking action
   │
   ▼
4. Grounded Generation (Gemini 2.0 Flash)
   └── Strict System Prompt (Forbidden to hallucinate unverified details)
   │
   ▼ (In case of external API failure)
   └── Deterministic Fallback Pipeline (Rule/Regex Engine)
   │
   ▼
Final Structured Response with Verified Sources
```

* **Intent Understanding**: Classifies queries across categories (e.g., `CAMPUS_INFORMATION`, `DEPARTMENT_INFORMATION`, `FACULTY_INFORMATION`, `FACILITY_INFORMATION`, `PROFESSOR_APPOINTMENT`).
* **Context Preservation**: Multi-turn conversation sessions retain contextual history for coherent follow-up questions.
* **Semantic Embeddings**: Knowledge records are transformed into vector representations for high-accuracy semantic retrieval, handling variations in student phrasing.
* **Verified Knowledge Base**: Extracted from official college documentation, including accredited B.Tech branches (CSE, CSE-DS, ECE, EEE, Mechanical, Civil), campus amenities (Central Library, Health Center, Canteen, Auditorium), and administrative leadership.
* **Grounded Fallback**: If an inquiry asks for non-public or unindexed data (e.g., personal phone numbers or unverified room numbers), the model gracefully acknowledges the limitation rather than fabricating an answer.

---

## 🔄 User & Appointment Workflows

### 1. Student Workflow
1. Register with username, email, password, and optional department/year details.
2. Sign in to access the **Student Dashboard**.
3. Launch the **AI Campus Enquiry Chatbot** to ask questions in English, Telugu, or Roman Telugu.
4. Navigate to the **Professors** tab to find faculty and inspect open 30-minute consultation slots.
5. Submit an appointment request with an academic agenda.
6. Track appointment state in the **Appointments** tab (`PENDING_APPROVAL` → `APPROVED` / `REJECTED`).
7. Cancel or reschedule appointments as necessary.

### 2. Professor Workflow
1. Register with department details and academic designation.
2. Account is marked `PENDING_APPROVAL` (login is prohibited until an Administrator approves the account).
3. Once approved, log in to the **Professor Dashboard**.
4. Review incoming student consultation requests in the **Pending Requests** queue.
5. Accept requests (changing status to `APPROVED`) or reject requests (with optional explanatory remarks).
6. View weekly appointment timetable and update available consultation slots.

### 3. Admin Workflow
1. Log in with administrative credentials to access the 12-tab **Admin Dashboard**.
2. **User Management**: Approve pending professor accounts, adjust roles, or deactivate users.
3. **Knowledge Base**: Insert new campus records, verify accuracy, or archive outdated entries.
4. **RAG Monitoring**: Check vector indexing health, initiate full reindexing, and run semantic query previews.
5. **Appointments Oversight**: Inspect all college appointment records, filter by status, and execute overrides when necessary.
6. **Audit Logs & Analytics**: Inspect immutable audit logs of all actions and review AI query distribution analytics.
7. **System Health**: Monitor live health statuses for API, MongoDB Atlas, and Gemini.

### 4. Appointment Lifecycle Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Student
    participant UI as React Web App
    participant API as FastAPI Backend
    participant DB as MongoDB Atlas
    actor Professor

    Student->>UI: Select faculty & 30-min available slot
    UI->>API: POST /api/appointments (Create Request)
    API->>DB: Store appointment (Status: PENDING_APPROVAL)
    API-->>UI: Confirmation & queue placement
    
    Professor->>UI: View Professor Dashboard queue
    UI->>API: GET /api/appointments/professor
    API->>DB: Fetch pending requests
    API-->>UI: Return pending list
    
    alt Professor Approves
        Professor->>UI: Click Approve
        UI->>API: POST /api/appointments/{id}/approve
        API->>DB: Update status to APPROVED
        API-->>UI: Appointment confirmed
    else Professor Rejects
        Professor->>UI: Click Reject (with optional note)
        UI->>API: POST /api/appointments/{id}/reject
        API->>DB: Update status to REJECTED & release slot
        API-->>UI: Status updated
    end

    Student->>UI: View updated appointment status
```

---

## 🔒 Authentication & Security

* **JWT-Based Authentication**: Stateless token generation using `python-jose` with configurable expiry (`JWT_EXPIRE_MINUTES`).
* **Role-Based Access Control (RBAC)**: Strict role demarcation (`student`, `professor`, `admin`) enforced by server-side FastAPI dependencies (`get_current_active_user`, `require_role`).
* **Resource Ownership Protection**: Students can only view, manage, or cancel their own appointments; professors can only respond to appointments booked with them; administrators hold monitored override authority.
* **Password Hashing**: Secure password hashing with Salt using `passlib[bcrypt]`.
* **Hardened HTTP Security Headers**:
  * `X-Content-Type-Options: nosniff`
  * `X-Frame-Options: DENY`
  * `Referrer-Policy: strict-origin-when-cross-origin`
* **CORS Isolation**: Controlled origins via `CORS_ORIGINS` configuration.
* **Sanitized Global Error Handling**: Unhandled exceptions return generic, non-leaking HTTP 500 error messages to prevent internal stack trace exposure.
* **Strict Secret Isolation**: No API keys, database credentials, or JWT secrets are bundled into client-side code; all secrets are managed exclusively on the server.

---

## 🛠️ Technology Stack

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Frontend Framework** | React 18 | Declarative single-page application |
| **Build Tool** | Vite 6 | Fast modern module bundler |
| **Styling & Icons** | Vanilla CSS + Tailwind CSS + Lucide React | Clean, responsive institutional theme |
| **Backend Framework** | FastAPI (Python 3.11) | High-performance asynchronous REST API |
| **ASGI Server** | Uvicorn | Production-ready ASGI web server |
| **Database** | MongoDB Atlas | Cloud-hosted NoSQL database with Motor async driver |
| **LLM Provider** | Google Gemini (`gemini-2.0-flash`) | Primary conversational AI model via Gemini API |
| **RAG & Search** | Vector Embeddings + Cosine Match | Semantic retrieval over official RGMCET documents |
| **Authentication** | JWT (`python-jose`) + Bcrypt (`passlib`) | Stateless tokens with role-based access control |
| **Calendar Service** | Google Calendar API / Service Abstraction | OAuth 2.0 integration with documented fallback |
| **Containerization** | Multi-stage Docker | Node 20 builder + Python 3.11-slim runtime |
| **Cloud Hosting** | Render | Automated web service container deployment |

---

## 📁 Project Structure

```
├── Dockerfile                         # Multi-stage Docker build (React builder + Python runtime)
├── render.yaml                        # Render blueprint configuration
├── docker-compose.yml                 # Local container orchestration specification
├── requirements.txt                   # Production Python dependencies
├── pytest.ini                         # Pytest test suite configuration
├── .env.example                       # Reference environment variable template
├── app/
│   ├── web_intents.py                 # Deterministic fallback intent matching rules
│   └── web_mvp/
│       ├── main.py                    # FastAPI entrypoint, middlewares, and SPA mounting
│       ├── config.py                  # Environment variable configuration loading
│       ├── auth.py                    # JWT authentication and password hashing logic
│       ├── auth_schemas.py            # Pydantic schemas for authentication
│       ├── schemas.py                 # Core schemas (appointments, chats, knowledge)
│       ├── store.py                   # MongoDB Atlas connection manager & async collections
│       ├── services.py                # Business logic for appointments and schedules
│       ├── knowledge.py               # Official RGMCET knowledge retrieval and grounding
│       ├── vector_store.py            # Semantic vector store interface
│       ├── embeddings.py              # Text embedding generation
│       ├── llm.py                     # LLM client abstraction (Gemini / OpenAI)
│       ├── agent.py                   # Multi-turn AI Agent orchestrator
│       ├── tools.py                   # Agent tool registry (search, appointments, availability)
│       ├── calendar_service.py        # Calendar integration and fallback abstraction
│       └── api/
│           ├── auth.py                # Endpoints: /api/auth (register, login, me)
│           ├── chat.py                # Endpoints: /api/chat (conversational inquiry)
│           ├── professors.py          # Endpoints: /api/professors (directory & schedule)
│           ├── appointments.py        # Endpoints: /api/appointments (booking & lifecycle)
│           └── admin.py               # Endpoints: /api/admin (users, knowledge, audit, RAG)
├── data/
│   ├── demo_professors.json           # Baseline verified faculty profiles
│   ├── demo_professor_schedules.json  # Standard weekly 30-minute consultation slots
│   └── rgmcet_knowledge/
│       ├── college_info.json          # Accreditation, vision, mission, leadership
│       ├── departments.json           # Academic programs, HODs, intake details
│       ├── facilities.json            # Campus facilities, library, sports, amenities
│       ├── timings.json               # College working hours and academic schedules
│       ├── vector_store.json          # Pre-computed semantic vector embeddings
│       └── faculty/                   # Departmental faculty records
├── frontend/
│   ├── package.json                   # Frontend scripts and npm dependencies
│   ├── vite.config.js                 # Vite bundler configuration
│   ├── tailwind.config.js             # Tailwind CSS design system tokens
│   ├── index.html                     # HTML5 single-page application entrypoint
│   └── src/
│       ├── main.jsx                   # React application mount
│       ├── App.jsx                    # Root routing and page shell
│       ├── styles.css                 # Global styling and custom design rules
│       ├── ErrorBoundary.jsx          # UI exception isolation boundary
│       ├── components/
│       │   ├── ChatWindow.jsx         # Conversational chat interface with sources
│       │   ├── ProfessorCard.jsx      # Faculty card with department and action buttons
│       │   └── Sidebar.jsx            # Multi-role navigation sidebar
│       ├── contexts/
│       │   └── AuthContext.jsx        # User state, JWT storage, login/logout handlers
│       ├── pages/
│       │   ├── Login.jsx              # User sign-in page
│       │   ├── Register.jsx           # User registration page
│       │   ├── StudentDashboard.jsx   # Student overview and quick actions
│       │   ├── Chat.jsx               # Dedicated AI campus assistant chat page
│       │   ├── Professors.jsx         # Faculty directory & appointment booking
│       │   ├── Appointments.jsx       # Student appointments tracking view
│       │   ├── ProfessorDashboard.jsx # Professor request approval dashboard
│       │   └── AdminDashboard.jsx     # Comprehensive 12-tab administrator portal
│       └── services/
│           └── api.js                 # Centralized Axios/fetch API client
├── scripts/
│   ├── seed_database.py               # Database initialization script
│   ├── test_mongodb_atlas.py          # MongoDB Atlas connectivity validation
│   └── verify_phase12_production.py   # Automated production browser verification suite
└── tests/
    ├── conftest.py                    # Shared pytest test fixtures
    ├── test_phase3_auth.py            # Authentication, registration & RBAC test cases
    ├── test_phase4.py                 # Multi-role dashboard test cases
    ├── test_phase10_admin.py          # Administrator dashboard and governance test cases
    ├── test_admin_appointment_workflow.py # End-to-end appointment lifecycle test cases
    ├── test_agent_queries.py          # Multilingual and grounding query test cases
    ├── test_llm_provider.py           # LLM provider abstraction and fallback test cases
    ├── test_knowledge.py              # Knowledge retrieval and grounding tests
    ├── test_web_api.py                # REST API route integration tests
    └── test_web_intents.py            # Deterministic fallback intent tests
```

---

## 🔑 Environment Variables

The application relies on the following environment variable names. For security, never commit real values or `.env` files into source control.

| Variable Name | Required | Description | Example Placeholder |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | Yes | Application environment | `production` or `development` |
| `PORT` | No | Server listen port (default: 8000) | `8000` |
| `MONGODB_URI` | Yes | MongoDB Atlas connection string | `mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority` |
| `DATABASE_NAME` | Yes | Database name in MongoDB | `rgmcet_ai_assistant` |
| `JWT_SECRET` | Yes | Secret key for signing JWT tokens | `<your-secure-random-secret>` |
| `JWT_EXPIRE_MINUTES` | No | Expiration time for access tokens | `60` |
| `LLM_PROVIDER` | Yes | AI model provider (`gemini` or `openai`) | `gemini` |
| `GEMINI_API_KEY` | Yes | Google Gemini API key | `<your-gemini-api-key>` |
| `GEMINI_MODEL` | No | Gemini model name | `gemini-2.0-flash` |
| `CORS_ORIGINS` | No | Allowed CORS origins (comma-separated) | `http://localhost:5173,https://rgmcet-ai-campus-assistant.onrender.com` |
| `GOOGLE_CALENDAR_ENABLED` | No | Toggle Google Calendar integration | `false` |
| `GOOGLE_CLIENT_ID` | No | Google OAuth 2.0 Client ID | `<your-google-client-id>` |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth 2.0 Client Secret | `<your-google-client-secret>` |
| `GOOGLE_REFRESH_TOKEN` | No | Google OAuth 2.0 Refresh Token | `<your-google-refresh-token>` |
| `GOOGLE_CALENDAR_ID` | No | Target Calendar ID | `primary` |

---

## 💻 Local Development Setup

### Prerequisites
* **Python**: 3.11+
* **Node.js**: 20+
* **MongoDB**: Local MongoDB instance or free MongoDB Atlas cluster

### 1. Clone the Repository
```bash
git clone https://github.com/challa-obulesh/RGMCET-AI-ASISTANCE-.git
cd RGMCET-AI-ASISTANCE-
git checkout main
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your local credentials and API keys
```

### 3. Backend Setup
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # On Linux/macOS: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend development server
uvicorn app.web_mvp.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API documentation is accessible at `http://127.0.0.1:8000/docs`.

### 4. Frontend Setup
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
The frontend development server starts at `http://localhost:5173`.

---

## 🚀 Production Deployment

### Containerized Deployment on Render
The application is packaged with a multi-stage Dockerfile that builds the React application into optimized static assets and serves them directly through FastAPI in a unified container.

1. **Create Web Service**: Connect your GitHub repository to [Render](https://render.com).
2. **Environment**: Select `Docker`.
3. **Branch**: `main`.
4. **Environment Variables**: Populate the production variables (`MONGODB_URI`, `DATABASE_NAME`, `JWT_SECRET`, `LLM_PROVIDER`, `GEMINI_API_KEY`, etc.) in the Render Dashboard.
5. **Health Check Path**: `/api/health`.

### MongoDB Atlas Cloud Database
1. Provision a free `M0` cluster on [MongoDB Atlas](https://www.mongodb.com/atlas).
2. Create a database user with read/write privileges.
3. Configure Network Access to allow traffic from anywhere (`0.0.0.0/0`) or Render outbound IP ranges.
4. Copy the connection URI into the `MONGODB_URI` environment variable on Render.

---

## 🧪 Testing & Verification Status

The project includes an extensive automated test suite covering all layers of the application.

```powershell
# Run the complete backend test suite
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

### Verified Testing Results:
* **Backend Test Suite**: **250 / 250 tests passing** (100% pass rate).
* **Frontend Production Build**: **Pass** (Clean Vite compilation into `frontend/dist` with zero errors).
* **Production Deployment**: Verified live and operational on Render.
* **MongoDB Atlas Persistence**: Read/write operations verified against cloud database.
* **Secret Hygiene Audit**: Completed with zero exposed credentials or keys across tracked Git files.
* **Browser Production Gates**: 55/55 production gates validated in Google Chrome across desktop and mobile viewports.

---

## 🛡️ Security Best Practices & Data Privacy Hardening

### 1. Synthetic Demo Email Policy
In compliance with RGMCET institutional data privacy guidelines, **no official faculty or staff email addresses are used in sample data, demonstration accounts, fixtures, or test seeds**.
* **Reserved Example Domains**: All demo accounts use reserved RFC 2606 domains (e.g. `@example.com`, `@example.org`, `@example.net`).
* **Canonical Demo Accounts**:
  * **Admin**: `admin@example.com`
  * **Professor / HOD**: `hod.cse.ds@example.com`
  * **Verified Faculty**: `prasad.cseds@example.com`, `samunnisa.cseds@example.com`, etc.
  * **Student**: `student1@example.com`
* **Real Identity Separation**: While public faculty names and designations are retained for campus directory lookup, personal contact credentials and authentication records are strictly decoupled and synthetic.

### 2. Centralized Privacy Gateway
Every outbound request destined for an external hosted LLM provider (such as Google Gemini or OpenAI) must pass through the backend `PrivacyGateway` ([privacy_gateway.py](file:///c:/Users/chall/OneDrive/Desktop/whatsapp%20ai%20agent/app/web_mvp/privacy_gateway.py)):
* **Data Minimization**: Only the specific user query and retrieved verified context needed to answer the question are transmitted.
* **Email Redaction**: Automatic detection and redaction of email addresses (`[REDACTED_EMAIL]`).
* **PII & Phone Redaction**: Phone numbers are redacted to `[REDACTED_PHONE]`.
* **Credential Redaction**: JWT tokens (`[REDACTED_TOKEN]`), MongoDB/SQL connection strings (`[REDACTED_DB_CONNECTION]`), passwords, and API keys are automatically stripped.
* **Prompt Boundary Separation**: System instructions, verified evidence context, and user input are strictly segregated into distinct payload blocks.
* **Safe Fallback**: If privacy sanitization encounters an unexpected exception, the outbound transmission is aborted immediately (`complete()` returns `None`) rather than risking unredacted data leakage.
* **Sanitized Logging**: Application logs never record raw prompts containing sensitive context or credentials; only sanitized metadata and redaction counts are logged.
* **Outbound Deep Inspection**: Final JSON payloads are recursively inspected before dispatch to guarantee no sensitive tokens or emails escape.

### 3. Role-Based Access Control (RBAC)
* **Backend Enforced**: All access control decisions (Student, Professor, Admin) are enforced in FastAPI route dependencies via JWT validation and role checks.
* **No LLM Authorization**: The system never relies on an LLM to decide or enforce access boundaries.
* **Cross-Professor Isolation**: Professors can view and manage only their own scheduled appointments. Modifying or approving another professor's schedule or appointments returns HTTP 403 Forbidden.

### 4. Deterministic Faculty Verification (Anti-Hallucination)
* **Deterministic Lookups**: Inquiries regarding specific faculty members (e.g., *"Is there any Data Science faculty member named Stephen?"*) are verified deterministically against official RGMCET records before any LLM interaction.
* **No Fictional Person Generation**: If no record matches, the system returns a verified no-match message:
  > *"No matching faculty member named Stephen was found in the verified Data Science faculty records."*
* The LLM is never permitted to invent faculty members or override verified database facts.

### 5. Known Privacy Limitations
* **Pattern-Based Matching**: The Privacy Gateway uses regular expressions and heuristic token analyzers. While effective against standard emails, phones, JWTs, and database URIs, it cannot guarantee 100% detection of oblique, fragmented, or adversarial PII patterns.
* **Response Generation Only**: The external LLM is utilized exclusively for natural language response generation; official institutional records stored in verified data files remain the authoritative source of truth.

### 6. Running Security & Privacy Tests
```powershell
# Run the dedicated automated privacy and security test suite (10 tests)
.\.venv\Scripts\python.exe -m pytest tests/test_privacy_security.py -v

# Run the complete regression test suite (250 tests passing)
.\.venv\Scripts\python.exe -m pytest tests/ -q

# Run visible Google Chrome end-to-end verification (headless=False)
.\.venv\Scripts\python.exe scripts/verify_phase7_chrome_full.py
```

---

## 🌿 Version Control, Branching & Release Management

The RGMCET AI Campus Assistant repository adheres to disciplined Git version control protocols, Conventional Commits, Semantic Versioning (SemVer), and automated GitHub Actions Continuous Integration (CI).

### 1. Repository Topology & Branch Roles

| Branch Name | Type | Purpose | Protected | Deployment Target |
| :--- | :--- | :--- | :---: | :--- |
| **`main`** | Primary / Trunk | Stable, production-ready codebase. All merged changes pass automated CI. | Yes | Render Production Web Service |
| **`feature/*`** | Topic Branch | Development of new user-facing features or system capabilities (e.g. `feature/security-privacy-demo-data`). | No | Local / Review Staging |
| **`fix/*`** / **`hotfix/*`** | Patch Branch | Targeted defect fixes and fast patches (e.g. `fix/faculty-lookup-anti-hallucination`). | No | Local / Review Staging |
| **`phase5`** .. **`phase12`** | Milestone Archive | Historical development phase snapshots capturing verification gates and architecture progression. | Preserved | Phase Verification Audits |

---

### 2. Git Flow & Release Lifecycle

The project follows a Trunk-Based Development with Feature Branches workflow:

```mermaid
gitGraph
    commit id: "v0.1.0"
    commit id: "v0.2.0"
    branch feature/security-privacy
    checkout feature/security-privacy
    commit id: "feat-privacy"
    commit id: "test-security"
    checkout main
    merge feature/security-privacy id: "pr-1-merge" tag: "v0.3.0"
    commit id: "fix-chat"
```

1. **Branch Out**: Create a focused branch from the latest `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/my-new-feature
   ```
2. **Develop & Test**: Implement changes locally and verify via automated pytest suite (250 tests):
   ```bash
   .\.venv\Scripts\python.exe -m pytest tests/ -q
   ```
3. **Commit with Conventions**: Follow the [Conventional Commits](#3-commit-message-conventions-conventional-commits) standard.
4. **Pull Request (PR)**: Open a PR on GitHub targeting `main`.
5. **Continuous Integration Gate**: Automated GitHub Actions CI workflow must pass all checks before merge approval.
6. **Deploy & Tag**: Merging into `main` automatically triggers Render deployment; create an annotated SemVer tag for release tracking.

---

### 3. Commit Message Conventions (Conventional Commits)

All commits in this repository conform to the [Conventional Commits Specification (v1.0.0)](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description in imperative mood>

[optional body providing deeper rationale]

[optional footer(s), e.g., Resolves #123]
```

#### Commit Types

| Type | Intent | Example from Repository History |
| :--- | :--- | :--- |
| **`feat`** | Introduces a new feature | `feat(privacy): fix generic secret regex, broaden API key & JWT patterns` |
| **`fix`** | Fixes a software defect or edge case | `fix(chat): ensure queries about nonexistent faculty return direct refusal` |
| **`docs`** | Documentation only updates | `docs(audit): record confirmed visible Chrome verification results` |
| **`test`** | Adds, refactors, or updates automated test suites | `test(e2e): verify browser workflows, improve chat UI, and add MongoDB fallback` |
| **`refactor`** | Code changes that neither fix a bug nor add a feature | `refactor(store): clean up async motor client connection life-cycle` |
| **`perf`** | Performance or query speed optimization | `perf(vector): pre-cache cosine embeddings for instant similarity lookup` |
| **`chore`** | Build scripts, dependencies, or configuration | `chore(deps): update requirements.txt with google-genai dependency` |
| **`ci`** | Changes to CI configuration or automation scripts | `ci(github): configure pytest regression matrix on Ubuntu runner` |

---

### 4. Semantic Versioning & Release Changelog

The repository follows [Semantic Versioning 2.0.0](https://semver.org/) (`vMAJOR.MINOR.PATCH`):
* **MAJOR**: Breaking API schema modifications or incompatible architectural pivots.
* **MINOR**: Backwards-compatible new features, portals, or major workflow additions.
* **PATCH**: Backwards-compatible bug fixes, security patches, or documentation improvements.

#### Release History

| Release Version | Date | Key Highlights & Changes |
| :--- | :--- | :--- |
| **`v0.3.0`** *(Current)* | Oct 2026 | **Security & Privacy Hardening**: Centralized `PrivacyGateway` (email/PII/JWT sanitization), synthetic RFC 2606 demo identities (`@example.com`), deterministic faculty verification (anti-hallucination guardrail), 250 passed automated pytest test cases, Chrome visible E2E verification suite. |
| **`v0.2.0`** | Oct 2026 | **Phase 10-12 Administrative Suite & Deployment**: 12-tab Admin dashboard, RAG vector index statistics & manual reindexing, Professor registration approval queue, Google Calendar OAuth service abstraction, multi-stage Docker build, and live Render deployment. |
| **`v0.1.0`** | Sep 2026 | **Web MVP & Core RAG Pipeline**: React 18 single-page app, FastAPI backend, semantic RAG over RGMCET knowledge, multi-role Student/Professor dashboards, 30-minute appointment booking engine, and JWT role-based security. |

---

### 5. Continuous Integration (CI) Workflow

Every push and pull request targeting `main` or `master` is automatically validated via GitHub Actions ([ci.yml](file:///c:/Users/chall/OneDrive/Desktop/whatsapp%20ai%20agent/.github/workflows/ci.yml)):

* **Runner Environment**: `ubuntu-latest`
* **Runtime**: Python `3.11`
* **Steps Executed**:
  1. `actions/checkout@v4`: Clean repository checkout.
  2. `actions/setup-python@v4`: Python 3.11 environment initialization with caching.
  3. Dependency Resolution: Installs `requirements.txt`, `pytest`, and `pytest-asyncio`.
  4. Test Execution: Runs `pytest -q` across all 250 unit, integration, and security test suites.

> [!IMPORTANT]
> Merging into `main` requires all automated tests in the CI pipeline to pass with 0 errors.

---

### 6. Release Tagging Protocol

To release a new version tag:

```bash
# 1. Ensure you are on the latest main branch with clean working directory
git checkout main
git pull origin main

# 2. Run the complete test suite to confirm 100% passing status
.\.venv\Scripts\python.exe -m pytest tests/ -q

# 3. Create an annotated git tag with release notes
git tag -a v0.3.0 -m "Release v0.3.0: Data Privacy Gateway, RFC 2606 Synthetic Identities & Anti-Hallucination Guardrails"

# 4. Push the tag to GitHub remote
git push origin v0.3.0
```

---

### 7. Developer Git Cheatsheet

```bash
# Clone the repository
git clone https://github.com/challa-obulesh/RGMCET-AI-ASISTANCE-.git
cd RGMCET-AI-ASISTANCE-

# Create a new feature branch
git checkout -b feature/appointment-rescheduling

# Inspect modified files and staging state
git status -s

# Stage changes
git add app/web_mvp/services.py tests/test_appointments.py

# Commit with Conventional Commit formatting
git commit -m "feat(appointments): add reschedule consultation endpoint with notification"

# Rebase feature branch on latest main before opening PR
git fetch origin
git rebase origin/main

# Push feature branch to GitHub remote
git push -u origin feature/appointment-rescheduling
```

---

## 🔮 Future Improvements

The following items are planned for future iterations and are clearly demarcated as upcoming work:
* **Multi-Channel Integrations**: Webhook-based integration with messaging channels such as WhatsApp and Telegram.
* **Automated Notifications**: Email and SMS alerts for upcoming appointments, schedule changes, and approval notifications.
* **Institutional SSO Integration**: Single Sign-On via Google Workspace / SAML for campus credentials.
* **Multi-Campus Multi-Tenant Scaling**: Support for multiple colleges or affiliated institutions on a unified infrastructure.

---

## 👨‍💻 Project Information & Governance

* **Institution**: Rajeev Gandhi Memorial College of Engineering and Technology (RGMCET)
* **Project**: AI Campus Assistant
* **Repository**: [https://github.com/challa-obulesh/RGMCET-AI-ASISTANCE-](https://github.com/challa-obulesh/RGMCET-AI-ASISTANCE-)
* **Primary Branch**: `main`
* **Current Version**: `v0.3.0`
* **Version Control**: Git + GitHub Actions CI
* **License**: Academic & Educational Use — Rajeev Gandhi Memorial College of Engineering and Technology