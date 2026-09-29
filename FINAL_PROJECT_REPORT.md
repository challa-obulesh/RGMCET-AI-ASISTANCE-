## Project

RGMCET AI Campus Assistant

## Current architecture

```text
React
 ↓
FastAPI
 ↓
Intent / Entity
 ↓
Verified RGMCET Knowledge
 ↓
Gemini / OpenAI
 ↓
Grounded Response
```

## Features completed

* RGMCET enquiry chatbot web interface (React + Tailwind)
* Hosted Gemini/OpenAI API integration for NLU classification and response generation
* Fallback local/regex intent matching when LLM unavailable
* Strict grounding against verified official RGMCET records
* English, Telugu, and Roman Telugu query understanding
* Professor directory, searchable profiles, and published weekly schedules
* Interactive 30-minute availability slots
* Appointment request workflow (creation, pending queue, approval/rejection)
* Graceful React ErrorBoundary for frontend stability

## Testing

Pytest: 103 passed, 0 failed
Compile: No compilation errors
Frontend build: Build successful (Vite production build)
Docker: Valid `docker-compose.yml` config
Browser: UI verified, no crashes on unknown/hallucination checks

## Browser validation

* **CSE Data Science query**: Correctly identified the 4-year B.Tech program and returned department information.
* **HOD query**: Correctly returned Dr. B. Bhaskara Rao as the HOD of CSE Data Science.
* **Central Library query**: Correctly identified the Central Library and verified its details while omitting exact campus coordinates since they weren't verified.
* **Telugu/Roman Telugu query**: Successfully parsed "CSE Data Science HOD evaru?" and returned the HOD information.
* **unknown information safety test**: When asked "What is the exact room number of the HOD?", the AI safely returned only the verified faculty information without hallucinating an unverified room number.

## Security

* `.env` not committed (ignored via `.gitignore`)
* API keys not exposed in source code (verified via grep)
* Frontend does not contain provider secrets (keys remain strictly server-side)
* No secrets in Git history from this final commit (initialized fresh repository)

## GitHub

Repository: https://github.com/challa-obulesh/RGMCET-AI-ASISTANCE-
Branch: main
Commit: 8f89528 (Ignore logs and scratch directory)
Push: SUCCESS
Working tree: CLEAN
