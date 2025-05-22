import subprocess
import sys
import json
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/scrape")
async def scrape(url: str = Query(..., description="Amazon product/search URL")):
   
    result = subprocess.run(
        [sys.executable, "app/scrape_worker.py", url],
        capture_output=True,
        text=True
    )
    try:
        data = json.loads(result.stdout)
    except Exception:
        data = {"error": "Failed to parse scraper output", "raw": result.stdout}
    return {"results": data}