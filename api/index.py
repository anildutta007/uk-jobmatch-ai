"""
Vercel Serverless Entrypoint for UK JobMatch AI FastAPI Backend.
"""

import sys
from pathlib import Path

# Add project root to sys.path so 'backend' package is resolvable on Vercel
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from backend.main import app
except Exception as e:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    err_text = traceback.format_exc()
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def catch_all(path: str):
        return PlainTextResponse(f"Startup Exception in Vercel:\n{err_text}", status_code=500)

