"""
Vercel Serverless Entrypoint for UK JobMatch AI FastAPI Backend.
"""

import os
import sys
import traceback
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/api/test")
def test_diag():
    return {
        "status": "ok",
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "files": os.listdir("."),
        "sys_path": sys.path
    }

try:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))

    from backend.main import api_router
    app.include_router(api_router, prefix="/api")
    app.include_router(api_router)
    backend_status = "loaded"
except Exception as e:
    backend_status = f"error: {traceback.format_exc()}"

@app.get("/api/backend-status")
def get_backend_status():
    return {"backend_status": backend_status}
