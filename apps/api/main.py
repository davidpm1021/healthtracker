from fastapi import FastAPI

app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"ok": True}

LATEST = {}

@app.post("/reading")
def reading(payload: dict):
    global LATEST
    LATEST = payload
    return {"status": "stored"}

@app.get("/")
def index():
    return {"latest": LATEST or None}
