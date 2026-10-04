# Phase 11 Production Hardening Plan

## 1. Current Architecture
The RGMCET AI Campus Assistant is a full-stack React and FastAPI web application. 
- **Frontend**: Vite + React single-page application (SPA) with routing handled client-side.
- **Backend**: FastAPI with async routes serving both API and static assets (when built).
- **Data Layer**: MongoDB with an in-memory JSON fallback for demo mode.
- **AI/LLM**: Integrates with OpenAI and Gemini via REST clients.

## 2. Existing Security Controls
- Standard CORS middleware is configured.
- Routes are protected via dependencies (OAuth2 JWT bearer token).
- Passwords are hashed using bcrypt.

## 3. Existing Authentication & Authorization
- **Authentication**: JWT-based stateless authentication (`access_token`).
- **Authorization**: Role-based access control (RBAC). Roles include `student`, `professor`, and `admin`.
- Currently, `require_admin`, `require_professor`, and `require_student` dependencies restrict access to role-specific endpoints.

## 4. Existing AI-Agent Safety
- The AI Agent (`agent.py`) uses a reasoning loop (ReAct pattern) with a predefined set of tools.
- It parses JSON responses from the LLM to trigger tool execution.
- If the LLM produces invalid JSON or hallucinates an unsupported tool, the agent catches the error or falls back to a legacy deterministic handler.

## 5. Existing RAG Grounding
- Knowledge base is stored in a LocalVectorStore using embeddings.
- Retrieves top 3 most relevant documents via cosine similarity.
- The retrieved documents are injected into the context window for grounding.
- If the LLM cannot confidently answer, it falls back to a deterministic unknown state.

## 6. Existing Database Handling
- Fallback system gracefully switches between MongoDB and in-memory lists depending on environment configuration.
- Connections are managed via context managers.

## 7. Existing Calendar Handling
- Integrates with Google Calendar using `google-api-python-client`.
- If credentials are not found, it gracefully disables the integration and proceeds without failing the appointment workflow.

## 8. Existing Frontend/API Architecture
- The React application communicates with the FastAPI backend using standard `fetch` wrappers.
- The backend mounts static assets to serve the frontend from a single port.

## 9. Current Weaknesses
- **Rate Limiting**: Missing from public endpoints (login, chat).
- **Security Headers**: Missing standard security headers (Content-Security-Policy, X-Frame-Options, etc.).
- **API Validation**: Some endpoints might lack strict Pydantic models for bounds checking (e.g., string lengths, enum bounds).
- **Secret Management**: Need to audit to ensure no hardcoded secrets exist.
- **Error Handling**: Some exceptions might propagate as 500s without sanitized details.

## 10. Phase 11 Implementation Plan
1. **Security Hardening**: Audit `auth.py` and endpoint permissions to ensure robust authorization for all sensitive operations (e.g., no cross-user appointment modification).
2. **API Validation**: Ensure all incoming POST/PUT request bodies use strict Pydantic validation.
3. **Secret Audit**: Search the codebase for leaked secrets and move them to `.env`.
4. **Security Headers & CORS**: Implement `Secure-Headers` middleware and restrict CORS wildcard origins appropriately based on `.env` settings.
5. **Rate Limiting**: Implement a lightweight in-memory sliding window rate limiter for critical endpoints (`/auth/login`, `/chat/agent`).
6. **AI Safety & RAG**: Tighten system prompts to prevent prompt injections; explicitly require LLM to reject out-of-bounds requests.
7. **Database & Error Handling**: Normalize exception returns across the API to hide stack traces and internal schema details.
8. **Frontend QA**: Review accessibility attributes and ensure graceful error messages for all API errors.

## 11. Verification Plan
We will augment the existing `verify_phase10_chrome.py` script into `verify_phase11_chrome.py` encompassing R01 through R60.
These test cases will run against the visible Google Chrome browser (headless=False) to validate end-to-end functionality, security controls, isolated scopes, and resilience to errors.

## 12. Deployment
**DEPLOYMENT IS STRICTLY OUT OF SCOPE FOR PHASE 11.** All activities relate only to code-level hardening.
