import time
import httpx

for i in range(10):
    try:
        r = httpx.get('http://127.0.0.1:8000/api/health', timeout=2.0)
        print('status', r.status_code, r.text)
        break
    except Exception as e:
        print('attempt', i, 'failed', e)
        time.sleep(1)
