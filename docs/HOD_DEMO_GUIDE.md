# RGMCET AI Campus Assistant — HOD Demonstration Guide

**Project Branch:** `feature/security-privacy-demo-data`  
**Base Commit:** `8f31fd4`  
**Target Audience:** Head of Department (HOD), Academic Evaluators, Security Auditors  
**Estimated Demo Duration:** 7–10 Minutes  

---

## 1. Executive Summary & Demo Goals

This guide provides an end-to-end walkthrough for demonstrating the RGMCET AI Campus Assistant to the Head of Department (HOD). It highlights key engineering improvements requested during recent security and privacy reviews:

1. **Complete Removal of Official Faculty Emails**: Demonstration fixtures and sample accounts strictly utilize synthetic addresses on the reserved `example.com` domain. Zero official institutional emails (`@rgmcet.edu.in`) are used as login credentials.
2. **Privacy Gateway & Data Redaction**: Real-time interceptor sanitizes all student PII, phone numbers, auth tokens, database URIs, and API credentials before payloads leave the server to external LLM providers (Gemini/OpenAI).
3. **Deterministic Anti-Hallucination**: Queries about unverified faculty (e.g., "Stephen" in Data Science) are rejected deterministically across English, Telugu, and Roman Telugu with zero fabricated profiles.
4. **Transparent Campus Grounding**: Inquiries regarding campus facilities (e.g., Central Library, Data Science Labs) cite verified architectural information from official pages while truthfully stating that room numbers and interior map coordinates are unlisted on official websites—preventing fabricated coordinates or fake Google Maps pins.
5. **Role-Based Access Control (RBAC) & Appointment Workflow**: Full student-to-professor consultation lifecycle with strict role isolation and admin approval enforcement.

---

## 2. System Prerequisites & Startup Commands

### Prerequisites
- **Operating System:** Windows, Linux, or macOS
- **Python:** 3.11 or 3.12 (virtual environment located in `.venv`)
- **Node.js:** Node.js v18+ (or bundled portable v20 in `node-v20.11.1-win-x64`)

### Terminal 1: Backend Startup (FastAPI)
Run the following in PowerShell from the project root:
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Start the FastAPI backend
python -m uvicorn app.web_mvp.main:app --host 127.0.0.1 --port 8000
```
- API Base URL: `http://127.0.0.1:8000`
- API Health Check: `http://127.0.0.1:8000/api/health`
- Interactive API Docs: `http://127.0.0.1:8000/docs`

> [!NOTE]
> The backend automatically initializes with in-memory fallback store (`DEMO_MODE=true`) if a live MongoDB instance is not connected. All demo features and user flows function seamlessly in both modes.

### Terminal 2: Frontend Startup (React + Vite)
Run the following in a second PowerShell window:
```powershell
cd frontend
..\node-v20.11.1-win-x64\npm.cmd run dev
```
- Web Application URL: `http://localhost:5173`

*(Alternatively, the compiled production build in `frontend/dist` is also served directly by FastAPI at `http://127.0.0.1:8000/` without needing a second terminal).*

---

## 3. Verified Demo Accounts & Setup Instructions

To preserve data privacy and adhere to institutional standards, all accounts use synthetic credentials. The system employs three distinct roles:

| Role | Email Address | Password | Purpose / Scope |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@example.com` | `AdminPass123!` | System oversight, user approvals, RAG diagnostics, audit logs. |
| **Professor** | `hod.cse.ds@example.com` | `Demo@Professor123` | Dr. B. Bhaskara Rao (Associate Professor & HOD). Review & approve consultation requests. |
| **Student** | `student1@example.com` | `Demo@Student123` | Submit campus enquiries, view faculty availability, book appointments. |

### Account Initialization Commands

If seeding a fresh local database or resetting accounts:

1. **Initialize Admin Account:**
   ```powershell
   python scripts/create_admin.py admin@example.com AdminPass123! "System Administrator"
   ```
2. **Seed Synthetic Faculty & Demo Appointments (when MongoDB is running):**
   ```powershell
   python scripts/seed_database.py
   ```
3. **On-the-Fly Web Registration:**
   - Any student can register immediately at `http://localhost:5173/register` by providing their name, any email (e.g., `student@example.com`), and a 6+ character password.
   - Professor accounts created through `/register` enter a `PENDING` queue and require one-click approval by the Admin before login is permitted.

---

## 4. 5–10 Minute Demonstration Script

### Act 1: Architecture & Data Privacy Hardening (1.5 Minutes)
**Goal:** Show the HOD that faculty privacy and student data are safeguarded.

1. **Inspect Fixtures:**
   - Open `data/demo_professors.json` and `official_faculty_registry.json`.
   - Point out that official faculty emails (`@rgmcet.edu.in`) have been completely scrubbed from login accounts and replaced with synthetic addresses (`@example.com`).
2. **Demonstrate Privacy Gateway Redaction:**
   - Explain that all LLM prompts pass through `app/web_mvp/privacy_gateway.py` before leaving the server.
   - Run the automated test in Terminal:
     ```powershell
     python -m pytest tests/test_privacy_security.py -k "test_privacy_gateway_redaction" -v
     ```
   - Show how email addresses, phone numbers, bearer tokens, and MongoDB URIs are stripped into `[REDACTED_*]` tokens before external dispatch.

---

### Act 2: Multilingual Campus Enquiry (2 Minutes)
**Goal:** Demonstrate the assistant's natural language comprehension across English, Telugu, and Roman Telugu.

Open `http://localhost:5173/` in the browser (or `http://127.0.0.1:8000/`).

1. **English Department Query:**
   - **Input:** `What is the intake of CSE Data Science?`
   - **Expected Result:** Explains the 4-year B.Tech specialization, citing an intake of 240, 160 credits, 8 semesters, and Dr. B. Bhaskara Rao as HOD, with verified URL citation (`https://www.rgmcet.edu.in/department-of-cseds.php`).
2. **Roman Telugu Campus Query:**
   - **Input:** `library ekkada undi?`
   - **Expected Result:** Understands the Roman Telugu phrasing. Responds: *"RGMCET official website prakaram: The official library page lists the Central Library and describes it as being in a spacious, separate, three-storied, fully air-conditioned building..."*
3. **Telugu Script Query:**
   - **Input:** `లైబ్రరీ ఎక్కడ ఉంది?`
   - **Expected Result:** Responds in Telugu script citing the verified three-storied Central Library building from official records.

---

### Act 3: Anti-Hallucination & Facility Truthfulness (2 Minutes)
**Goal:** Prove the AI does not invent nonexistent people, fake details, or dummy map links.

1. **Nonexistent Faculty Check ("Stephen"):**
   - **Input:** `Is there any Data Science faculty member named Stephen?`
   - **Expected Result:** Deterministically responds: *"No matching faculty member named Stephen was found in the verified Data Science faculty records. This person is not listed in the verified faculty records."*
   - **Telugu Check:** `డేటా సైన్స్ విభాగంలో Stephen అనే ఫ్యాకల్టీ ఉన్నారా?`
   - **Expected Result:** Responds in Telugu confirming Stephen is not in current records (`కనుగొనబడలేదు`).
2. **Existing Faculty Check:**
   - **Input:** `Tell me about Dr. Penchala Prasad`
   - **Expected Result:** Correctly confirms Dr. P. Penchala Prasad as Associate Professor in Data Science with official profile link.
3. **Location Grounding (Truthful Admission vs Fake GPS):**
   - **Input:** `Data Science lab ekkada undi?`
   - **Expected Result:** Identifies the CSE Data Science labs, but explicitly clarifies that interior room numbers or building coordinates are unverified in official publications. It does **not** generate fabricated Google Maps links or dummy pins.
4. **Unsupported Topic Safe Fallback:**
   - **Input:** `What is the dinner menu tonight at the hostel?`
   - **Expected Result:** Does not invent a menu. Safely responds: *"I couldn't find a verified answer in the RGMCET knowledge available to me."*

---

### Act 4: Appointment Workflow & RBAC (3 Minutes)
**Goal:** Demonstrate student consultation booking and professor review.

1. **Student Logs In & Books Appointment:**
   - Navigate to `http://localhost:5173/login`.
   - Sign in as `student1@example.com` / `Demo@Student123`.
   - Click on the **Professors** tab in the sidebar.
   - Locate **Dr. B. Bhaskara Rao** and click **Request appointment**.
   - Enter purpose: `Academic Project Consultation`.
   - Submit request.
   - Navigate to **My Appointments** (Student Dashboard) and show status: `⏳ PENDING PROFESSOR APPROVAL`.
   - Click **Log out** in the lower-left sidebar.

2. **Professor Reviews & Approves:**
   - Navigate to `/login`.
   - Sign in as `hod.cse.ds@example.com` / `Demo@Professor123`.
   - Point out the **Professor Dashboard** displaying professor identity header and pending requests.
   - Under **Pending Student Requests**, locate the appointment from `student1@example.com`.
   - Click **Approve**.
   - Show that the appointment immediately moves to **Upcoming Confirmed Appointments** with status `APPROVED`.
   - Click **Log out**.

3. **Student Observes Confirmed Status:**
   - Log back in as `student1@example.com`.
   - Show the Student Dashboard: Status is updated in real time to `✓ APPROVED`.

4. **RBAC Security Boundary:**
   - Attempt to manually type `http://localhost:5173/admin/dashboard` in the student's browser URL bar.
   - Show that access is blocked with an **Access Denied** message, proving strict role separation.

---

### Act 5: Administrator Governance (1.5 Minutes)
**Goal:** Show administrative management and auditing controls.

1. Navigate to `/login` and sign in as `admin@example.com` / `AdminPass123!`.
2. Review Admin Tabs:
   - **Overview:** Active user counts, pending approvals, and system metrics.
   - **Professor Approvals:** Illustrate where new faculty registrations require admin activation before they can log in.
   - **Knowledge Base:** Campus records with official verification flags.
   - **RAG & Agent:** Vector index statistics and tool diagnostics.
   - **Audit Logs:** Immutable log of system actions and role assignments.

---

## 5. Live Privacy Redaction Verification

To provide technical proof of outbound redaction to technical faculty, execute this one-liner in Python:

```powershell
python -c "from app.web_mvp.privacy_gateway import privacy_gateway; sys_out, usr_out, stats = privacy_gateway.sanitize_request('System prompt', 'Student roll 21091A3201 email student@rgmcet.edu.in phone 9849348501 token eyJhbGciOiJIUzI1NiJ9.demo'); print('Sanitized:', usr_out); print('Stats:', stats)"
```

**Output:**
```
Sanitized: Student roll 21091A3201 email [REDACTED_EMAIL] phone [REDACTED_PHONE] token [REDACTED_TOKEN]
Stats: {'emails': 1, 'phones': 1, 'tokens': 1, 'db_uris': 0, 'api_keys': 0, 'passwords': 0}
```

---

## 6. Implementation Truth Matrix (What Is vs What Is Not)

To maintain academic integrity during the presentation, keep actual capabilities distinct from future roadmap items:

| Capability | Current Verified Implementation | Unimplemented / Roadmap (Do Not Claim) |
| :--- | :--- | :--- |
| **Data Privacy** | Pre-dispatch Regex & Pattern Sanitizer (`[REDACTED_*]`) for LLM prompts; fail-closed safety. | Full AI-based Named Entity Recognition (NER) token classifier. |
| **Faculty Data** | 100% synthetic demo accounts; official faculty registry mapped from public college web pages. | Real personal email addresses or private cell phone numbers. |
| **Faculty Queries** | Deterministic lookup prevents inventing professors (e.g. Stephen). | Guessing faculty schedules when not published on college portal. |
| **Location/Maps** | Truthful quoting of building attributes (e.g., 3-storied Central Library); states room coordinates are unverified. | Real-time GPS indoor navigation or Google Maps route links. |
| **Channels** | Web Application (FastAPI + React 18 SPA) on desktop and mobile. | Telegram Bot or WhatsApp Bot integrations (Documented roadmap items). |
| **Fallback** | Seamless local template & regex intent fallback when LLM is unavailable or offline. | Unrestricted open-domain conversational chitchat outside RGMCET domain. |

---

## 7. Troubleshooting & FAQ for the Demo

### Q1: The backend fails to start with "Address already in use"
**Fix:** Another process is occupying port 8000. Terminate the existing instance or select another port:
```powershell
# Find and terminate process on port 8000
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
```

### Q2: Professor cannot log in ("Account pending admin approval")
**Fix:** The professor account was registered fresh and requires approval.
1. Log in as `admin@example.com` / `AdminPass123!`.
2. Go to **Professor Approvals** tab.
3. Click **Approve** next to the professor.
4. Return to login.

### Q3: How does the assistant behave without internet or API keys?
**Fix:** The platform has a built-in deterministic fallback engine. If `GEMINI_API_KEY` is absent or offline, questions about departments, intake, library, and faculty will still answer accurately using local regex intent matching and local knowledge fixtures.

### Q4: Can students see other students' appointments?
**Fix:** No. All appointment queries are filtered by authenticated `student_id` in the JWT token.
