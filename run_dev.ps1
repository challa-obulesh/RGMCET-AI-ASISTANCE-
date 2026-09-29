# Run the web API using its in-memory demo data when MongoDB is unavailable.
# Usage: PowerShell -> ./run_dev.ps1

$env:DEMO_MODE = "true"
pip install -r requirements.txt
uvicorn app.web_mvp.main:app --reload --port 8000
