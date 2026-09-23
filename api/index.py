"""
Vercel Serverless Entrypoint for UK JobMatch AI FastAPI Backend.
"""

import sys
from pathlib import Path

# Add project root to sys.path so 'backend' package is resolvable on Vercel
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.main import app
