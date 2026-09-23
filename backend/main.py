"""
Main FastAPI Application for AI Job Matcher & Scorer
Serves the API and modern web frontend.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Ensure current and parent directory are on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.cv_parser import parse_cv_document
from backend.job_services import aggregate_uk_jobs
from backend.gemini_agent import extract_cv_profile, score_jobs_with_gemini

app = FastAPI(
    title="AI Job Matcher & Scorer",
    description="UK-focused job matching engine powered by Google Gemini",
    version="1.0.0"
)

# Enable CORS for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = BASE_DIR / "frontend"


from fastapi import APIRouter

api_router = APIRouter()

FALLBACK_SAMPLE_CV = """Alex Turner
London, United Kingdom | alex.turner.dev@example.co.uk | +44 7700 900123
LinkedIn: linkedin.com/in/alex-turner-tech | GitHub: github.com/alexturner-dev

PROFESSIONAL SUMMARY
Senior Full-Stack Software Engineer with 6+ years of commercial experience architecting, building, and deploying scalable web applications and cloud microservices in fast-paced UK tech environments. Passionate about modern JavaScript/TypeScript, React, Python (FastAPI/Django), REST/GraphQL APIs, and AWS cloud infrastructure. Proven track record of reducing API latency by 45% and leading cross-functional engineering teams.

CORE TECHNICAL SKILLS
- Languages: Python, TypeScript, JavaScript (ES6+), SQL, HTML5, CSS3
- Frontend: React, Next.js, Redux Toolkit, Tailwind CSS, Vue.js
- Backend: FastAPI, Django, Flask, Node.js, Express.js, RESTful APIs, GraphQL
- Databases: PostgreSQL, MongoDB, Redis, MySQL
- Cloud & DevOps: AWS (EC2, S3, Lambda, ECS), Docker, Kubernetes, CI/CD (GitHub Actions), Terraform
- Methodologies: Agile/Scrum, Test-Driven Development (TDD), Jest, PyTest, Microservices Architecture

WORK EXPERIENCE

Senior Full-Stack Developer | FinTech Solutions Ltd (London, UK)
March 2022 - Present
- Spearheaded the design and delivery of a real-time UK payment processing dashboard using React, TypeScript, and FastAPI, handling over 2M transactions daily.
- Optimized database indexing and Redis caching, resulting in a 45% reduction in API response times.
- Managed AWS cloud infrastructure using Terraform and automated deployments via GitHub Actions CI/CD pipelines.

Software Engineer | CloudScale Systems (Manchester, UK - Remote)
July 2019 - February 2022
- Developed scalable customer-facing SaaS portals using React, Node.js, and PostgreSQL.
- Built microservices in Python (Flask/FastAPI) integrated with third-party CRM and banking APIs.
- Containerized legacy applications using Docker and migrated workloads to AWS ECS.

EDUCATION & CERTIFICATIONS
- B.Sc. (Hons) in Computer Science (First Class) - University of Manchester (2015 - 2018)
- AWS Certified Solutions Architect - Associate (2023)
"""


class SaveKeyRequest(BaseModel):
    api_key: str


@api_router.get("/config")
async def get_config():
    """Returns application configuration status and API key detection."""
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    has_key = bool(env_key and env_key != "your_gemini_api_key_here")
    return {
        "has_gemini_key": has_key,
        "default_country": os.getenv("DEFAULT_COUNTRY", "gb"),
        "default_location": os.getenv("DEFAULT_LOCATION", "United Kingdom"),
        "adzuna_configured": bool(os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY")),
        "reed_configured": bool(os.getenv("REED_API_KEY"))
    }


@api_router.post("/save-key")
async def save_api_key(req: SaveKeyRequest):
    """Saves the Gemini API key to local .env file."""
    api_key = req.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    env_path = BASE_DIR / ".env"
    lines = []
    found = False

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    lines.append(f"GEMINI_API_KEY={api_key}\n")
                    found = True
                else:
                    lines.append(line)

    if not found:
        lines.insert(0, f"GEMINI_API_KEY={api_key}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        # In serverless environments .env is read-only
        pass

    # Update runtime environment variable
    os.environ["GEMINI_API_KEY"] = api_key
    return {"success": True, "message": "Gemini API key successfully saved"}


@api_router.get("/sample-cv")
async def get_sample_cv():
    """Returns the pre-loaded sample CV text for instant 1-click testing."""
    sample_path = BASE_DIR / "sample_cv.txt"
    if sample_path.exists():
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            content = FALLBACK_SAMPLE_CV
    else:
        content = FALLBACK_SAMPLE_CV

    return {
        "filename": "Alex_Turner_Senior_FullStack_CV.txt",
        "content": content
    }


@api_router.post("/match-jobs")
async def match_jobs(
    file: Optional[UploadFile] = File(None),
    cv_text: Optional[str] = Form(None),
    target_location: Optional[str] = Form("United Kingdom"),
    min_score: Optional[float] = Form(0.0),
    custom_api_key: Optional[str] = Form(None)
):
    """
    Main pipeline:
    1. Parse CV (Uploaded document or raw text)
    2. Extract skills & profile via Gemini LLM agent
    3. Aggregate UK jobs across providers
    4. Deep score jobs against CV out of 10 using Gemini
    """
    try:
        # Step 1: Extract Text
        extracted_text = ""
        filename = "uploaded_cv"
        if file and file.filename:
            filename = file.filename
            content = await file.read()
            if content:
                extracted_text = parse_cv_document(filename, content)

        if not extracted_text and cv_text and cv_text.strip():
            extracted_text = cv_text.strip()
            filename = "pasted_cv.txt"

        if not extracted_text:
            raise HTTPException(
                status_code=400,
                detail="Please upload a CV document (.pdf, .docx, .txt) or provide CV text."
            )

        # Step 2: Extract CV Profile & Search Keywords
        active_api_key = custom_api_key or os.getenv("GEMINI_API_KEY")
        cv_profile = extract_cv_profile(extracted_text, active_api_key)

        # Step 3: Fetch & Aggregate UK Jobs
        keywords = cv_profile.get("search_keywords", ["Full Stack Developer", "Python", "React"])
        raw_jobs = await aggregate_uk_jobs(
            search_keywords=keywords,
            target_location=target_location or "United Kingdom",
            max_results=12
        )

        # Step 4: Score Jobs via Gemini LLM Agent
        scored_jobs = score_jobs_with_gemini(cv_profile, raw_jobs, active_api_key)

        # Filter by minimum score if specified
        if min_score and min_score > 0:
            scored_jobs = [j for j in scored_jobs if j.get("match_score", 0) >= min_score]

        return {
            "success": True,
            "filename": filename,
            "profile": cv_profile,
            "jobs": scored_jobs,
            "count": len(scored_jobs),
            "ai_powered": cv_profile.get("ai_powered", False)
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Include router under both /api and root prefix so all Vercel route variants match seamlessly
app.include_router(api_router, prefix="/api")
app.include_router(api_router)


# Mount static assets for web frontend (supports both public/ for Vercel and frontend/ for local dev)
PUBLIC_DIR = BASE_DIR / "public"
STATIC_DIR = PUBLIC_DIR if PUBLIC_DIR.exists() else FRONTEND_DIR

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/styles.css")
    async def serve_styles():
        return FileResponse(STATIC_DIR / "styles.css")

    @app.get("/app.js")
    async def serve_app_js():
        return FileResponse(STATIC_DIR / "app.js")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
