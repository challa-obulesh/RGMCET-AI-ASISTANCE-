# Run the RGMCET AI Campus Assistant web API locally.

pip install -r requirements.txt
uvicorn app.web_mvp.main:app --reload --port 8000
