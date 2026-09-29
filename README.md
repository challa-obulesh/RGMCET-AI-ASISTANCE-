# RGMCET AI Campus Assistant

### Overview
A web-based AI campus assistant for RGMCET students.

### Features
* RGMCET enquiry chatbot
* Verified official RGMCET knowledge
* Gemini/OpenAI hosted LLM support
* English
* Telugu
* Roman Telugu
* Faculty information
* Department information
* Campus facilities
* Professor availability
* Appointment requests
* Appointment approval/rejection/cancellation
* Grounded AI responses
* FastAPI backend
* React frontend

### Architecture
```text
React Web App
      ↓
FastAPI
      ↓
Intent + Entity Detection
      ↓
Verified RGMCET Knowledge
      ↓
Gemini / OpenAI
      ↓
Grounded Response
```

### Backend setup
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.\.venv\Scripts\uvicorn.exe app.web_mvp.main:app --port 8000 --reload
```

### Frontend setup
```powershell
cd frontend
npm install
npm run dev
```

### Environment variables
See `.env.example`. Do not commit real API keys in the `.env` file.
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.0-flash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
MONGODB_URI=
DATABASE_NAME=rgmcet_ai
```

### Testing
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```
Current test suite has 103 tests passing.