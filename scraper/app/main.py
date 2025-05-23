import subprocess
import sys
import json
import os
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
async def scrape(url: str = Query(..., description="Amazon product/search URL"),
                extract_metadata: bool = Query(False),
                get_alternates: bool = Query(False)):
    script_path = os.path.abspath("app/scrape_worker.py")
    print("[DEBUG] Running:", sys.executable, script_path, url)
    print("[DEBUG] File exists:", os.path.exists(script_path))
  
    args = [sys.executable, script_path, url]
    if extract_metadata:
        args.append("--extract-metadata")
    if get_alternates:
        args.append("--get-alternates")
    print("[DEBUG] Running:", " ".join(args))
    result = subprocess.run(
        args,
        capture_output=True,
        text=True
    )
    print("[SCRAPER STDERR]", result.stderr)
    try:
        data = json.loads(result.stdout)
    except Exception:
        data = {"error": "Failed to parse scraper output", "raw": result.stdout}
    return {"results": data, "stderr": result.stderr, "returncode": result.returncode}