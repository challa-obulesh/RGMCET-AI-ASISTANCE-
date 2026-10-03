# RGMCET AI Campus Assistant — Production Deployment Guide

This guide details the procedure to deploy, secure, configure, and operate the RGMCET AI Campus Assistant in a production web environment.

---

## 1. Required Software

- **Python**: 3.10 or higher
- **Node.js**: v18.0.0 or higher
- **npm**: 9.0.0 or higher
- **MongoDB**: MongoDB Atlas cluster (MongoDB 6.0+) or self-hosted MongoDB instance
- **Process Manager**: systemd, Docker, or PM2 / uvicorn / Gunicorn for backend execution
- **Web Server / Reverse Proxy**: NGINX, Cloudflare, or AWS CloudFront/ALB (for TLS termination & static frontend hosting)

---

## 2. Environment Variables

The backend application is configured via environment variables. Copy `.env.example` to `.env` and fill in your production values. **Never commit `.env` or any production secrets to Git.**

### Backend (`.env`)

| Variable | Required | Description | Example |
|---|---|---|---|
| `LLM_PROVIDER` | Yes | Hosted LLM provider (`gemini` or `openai`) | `gemini` |
| `GEMINI_API_KEY` | If provider=gemini | Google Gemini API key | `AIzaSy...` |
| `GEMINI_MODEL` | No | Gemini model name | `gemini-2.0-flash` |
| `OPENAI_API_KEY` | If provider=openai | OpenAI API key | `sk-proj-...` |
| `OPENAI_MODEL` | No | OpenAI model name | `gpt-4o-mini` |
| `MONGODB_URI` | Yes (in Prod) | MongoDB connection string | `mongodb+srv://<user>:<password>@cluster0.xxx.mongodb.net/?retryWrites=true&w=majority` |
| `DATABASE_NAME` | No | Database name | `rgmcet_ai_assistant` |
| `JWT_SECRET` | Yes (in Prod) | Cryptographically random secret for JWT signing | `6f8d9a2b4...` (32+ chars) |
| `JWT_EXPIRE_MINUTES` | No | Token expiration duration (minutes) | `60` |
| `CORS_ORIGINS` | Yes (in Prod) | Comma-separated list of allowed frontend origins | `https://campus.rgmcet.edu.in` |
| `DEMO_MODE` | Yes | Set `false` in production for full database persistence | `false` |

### Frontend (`frontend/.env` or build-time environment)

| Variable | Required | Description | Example |
|---|---|---|---|
| `VITE_API_BASE_URL` | Yes | Base URL for FastAPI endpoints | `https://api.campus.rgmcet.edu.in/api` |

---

## 3. Local Setup & Verification

1. **Clone repository**:
   ```bash
   git clone https://github.com/challa-obulesh/RGMCET-AI-ASISTANCE-.git
   cd RGMCET-AI-ASISTANCE-
   ```

2. **Create Python virtual environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Frontend dependencies**:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

---

## 4. Backend Startup

### Development Mode

```powershell
$env:PYTHONPATH="."
.venv\Scripts\python.exe -m uvicorn app.web_mvp.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Mode

Using Gunicorn with Uvicorn workers (Linux production environment):

```bash
gunicorn app.web_mvp.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 5. Frontend Startup & Build

### Development Mode

```bash
cd frontend
npm run dev
```

### Production Build

```bash
cd frontend
npm run build
```

The compiled static assets will be located in `frontend/dist/`. Serve these assets using NGINX, Cloudflare Pages, Vercel, or AWS S3 + CloudFront.

---

## 6. MongoDB Atlas Setup

1. Create a cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Create a Database User with read/write access to `rgmcet_ai_assistant`.
3. Network Access: Add IP access rules for your production application server IPs.
4. Copy the connection string:
   `mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority`
5. Set `MONGODB_URI` and `DEMO_MODE=false` in your production backend environment.

---

## 7. LLM API Configuration

### Google Gemini (Recommended)

1. Obtain an API key from Google AI Studio.
2. Set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=<your-key>`.
3. Default model: `gemini-2.0-flash`.

### Fallback Behavior

If the hosted LLM API becomes temporarily unavailable or rate-limited, the system automatically falls back to deterministic, grounded local campus information responses without crashing.

---

## 8. CORS Configuration

In production, set `CORS_ORIGINS` to match your exact frontend domain(s):

```env
CORS_ORIGINS=https://rgmcet-ai.edu.in,https://app.rgmcet-ai.edu.in
```

Do **NOT** use `*` in production.

---

## 9. Production Deployment Steps

1. Provision Linux Server (Ubuntu 22.04 LTS / Debian 12) or Container Cluster.
2. Set up SSL/TLS certificate via Let's Encrypt / certbot or Cloudflare.
3. Configure systemd service for FastAPI app (`/etc/systemd/system/rgmcet-backend.service`).
4. Configure NGINX reverse proxy for API requests (`/api`) and static file serving for `frontend/dist`.
5. Verify health check endpoint at `https://your-domain.com/api/health`.

---

## 10. Security Checklist

- [x] All secrets kept in `.env` and environment variables.
- [x] Passwords hashed using bcrypt.
- [x] JWT authentication enabled with strong random secret (`JWT_SECRET`).
- [x] Role-based authorization enforced (Students cannot approve/reject appointments or access professor dashboards).
- [x] Input parameters validated via Pydantic schemas.
- [x] Unhandled exceptions produce safe 500 error responses without stack traces.
- [x] Explicit CORS origin whitelist configured.
- [x] API key leak prevention verified.

---

## 11. Health-Check Endpoint

- **Endpoint**: `GET /api/health` or `GET /health`
- **Response**:
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

## 12. Troubleshooting

| Issue | Potential Cause | Solution |
|---|---|---|
| `503 Service Unavailable` on appointment endpoints | MongoDB connection failed in non-demo mode | Check `MONGODB_URI` and Atlas network access whitelist |
| `401 Unauthorized` | Missing/expired Bearer token | Ensure user is logged in; refresh token if expired |
| `403 Forbidden` | Role mismatch | Student attempting professor operation or accessing unauthorized queue |
| LLM timeout | Network latency or API limit | Application falls back to local knowledge base automatically |

---

## 13. How to Run Tests

### Backend Unit & Integration Tests

```powershell
$env:PYTHONPATH="."
.venv\Scripts\python.exe -m pytest tests\ -v
```

### Frontend Build Verification

```bash
cd frontend
npm run build
```

### Playwright E2E Browser Tests

```bash
npx playwright test
```
