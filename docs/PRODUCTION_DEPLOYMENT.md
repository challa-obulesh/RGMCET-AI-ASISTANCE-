# RGMCET AI Campus Assistant — Production Deployment Guide

## Prerequisites
- Python 3.9+
- Node.js 18+ (for frontend build)
- MongoDB (Local or Atlas)
- LLM API Key (Gemini or OpenAI)

## Environment Variables

### Backend (`.env`)
Create a `.env` file in the root directory. NEVER commit this file to version control.

```env
# ---- LLM Configuration (server-side only) ----
LLM_PROVIDER=gemini # or openai
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash

# ---- Database ----
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=rgmcet_ai_assistant

# ---- Security ----
# Generate a secure secret using: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=your_super_secret_jwt_key
JWT_EXPIRE_MINUTES=60

# ---- CORS ----
# Comma-separated list of allowed frontend origins
CORS_ORIGINS=https://your-production-domain.example
```

### Frontend (`frontend/.env` or `frontend/.env.local`)
Create an environment file in the `frontend/` directory.

```env
VITE_API_BASE_URL=/api
```
*(By default, if served from the same domain by the FastAPI backend, this can just be `/api` or omitted entirely).*

## Local Setup

### 1. Backend Setup
1. Clone the repository and navigate to the root directory.
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your `.env` file as described above.

### 2. Frontend Setup
1. Navigate to the `frontend/` directory.
2. Install dependencies:
   ```bash
   npm install
   ```

## Production Deployment Instructions

### 1. Build the Frontend
From the `frontend/` directory, run:
```bash
npm run build
```
This generates production-ready static files in the `frontend/dist/` directory.

### 2. Start the Backend (with Frontend Served)
The FastAPI backend is configured to serve the frontend static files automatically if they exist in `frontend/dist/` and no API route matches.

Start the FastAPI application using Uvicorn:
```bash
uvicorn app.web_mvp.main:app --host 0.0.0.0 --port 8000
```

*Note: For production, consider using Gunicorn with Uvicorn workers:*
```bash
gunicorn app.web_mvp.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Security Checklist
- [ ] Ensure `.env` is in `.gitignore` and not committed.
- [ ] Generate a strong, random `JWT_SECRET`.
- [ ] Restrict `CORS_ORIGINS` to your actual frontend domain (do not use `*`).
- [ ] Restrict MongoDB network access to your production server IPs (if using Atlas).
- [ ] Ensure no API keys or database credentials are included in the frontend source code.

## Health Endpoint
To verify the application is running and the database/LLM connections are working:
```bash
curl http://your-domain/health
```
Response format:
```json
{
  "status": "ok",
  "demo_mode": false,
  "database": "connected",
  "llm_provider": "gemini",
  "version": "0.3.0"
}
```

## Troubleshooting
- **Frontend not loading:** Ensure you ran `npm run build` in the `frontend/` directory and that `frontend/dist/` exists.
- **CORS errors:** Verify that the frontend URL is exactly matched in `CORS_ORIGINS` in your `.env` file.
- **Database connection failure:** Check your `MONGODB_URI` and ensure your server IP is allowed in MongoDB Atlas network settings.
- **LLM errors:** Verify `LLM_PROVIDER` and the corresponding API keys in `.env`. Ensure your API keys have sufficient quota.

## Test Commands
**Backend Tests:**
```bash
PYTHONPATH="." pytest tests/ -v
```

**Frontend Tests (if applicable):**
```bash
cd frontend && npm test
```
