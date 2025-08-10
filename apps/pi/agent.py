import os, time, json, requests, random
from datetime import datetime, timezone

API = os.getenv("API_URL","http://localhost:8000")

def make_reading():
    return {"temp": round(20 + random.random()*5, 2),
            "ts": datetime.now(timezone.utc).isoformat()}

if __name__ == "__main__":
    while True:
        try:
            r = requests.post(f"{API}/reading", json=make_reading(), timeout=5)
            print("POST", r.status_code)
        except Exception as e:
            print("ERR", e)
        time.sleep(10)
