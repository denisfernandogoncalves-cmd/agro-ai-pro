from fastapi import FastAPI

app = FastAPI(title="AGRO AI PRO")

@app.get("/")
def root():
    return {"status": "ok", "project": "AGRO AI PRO"}
