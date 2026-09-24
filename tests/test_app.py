"""
Automated Test Suite for UK JobMatch AI
Tests parser, job aggregator, scoring engine, and FastAPI endpoints.
"""

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import asyncio
from backend.cv_parser import parse_cv_document
from backend.job_services import aggregate_uk_jobs, pre_filter_and_rank_jobs, CURATED_UK_JOBS
from backend.gemini_agent import extract_cv_profile_fallback, score_jobs_heuristic
from fastapi.testclient import TestClient
from backend.main import app


def test_cv_parser():
    sample_path = BASE_DIR / "sample_cv.txt"
    assert sample_path.exists(), "sample_cv.txt must exist"
    
    with open(sample_path, "rb") as f:
        content = f.read()
        
    text = parse_cv_document("sample_cv.txt", content)
    assert "Alex Turner" in text, "CV parser must extract candidate name"
    assert "Python" in text, "CV parser must extract Python skill"
    print("PASS: CV Parser extracted text successfully.")


def test_job_aggregation():
    async def _run():
        jobs = await aggregate_uk_jobs(["Python", "React", "AWS"], target_location="London", max_results=5)
        assert len(jobs) > 0, "Aggregator should return jobs"
        for job in jobs:
            assert "title" in job, "Job must have a title"
            assert "company" in job, "Job must have a company"
            assert "location" in job, "Job must have a location"
        print(f"PASS: Aggregated {len(jobs)} UK jobs successfully.")

    asyncio.run(_run())


def test_heuristic_scoring():
    sample_path = BASE_DIR / "sample_cv.txt"
    with open(sample_path, "r", encoding="utf-8") as f:
        cv_text = f.read()

    profile = extract_cv_profile_fallback(cv_text)
    assert profile["candidate_name"] == "Alex Turner"
    assert len(profile["core_technical_skills"]) > 0

    scored = score_jobs_heuristic(profile, CURATED_UK_JOBS[:4])
    assert len(scored) == 4
    for job in scored:
        assert 1.0 <= job["match_score"] <= 10.0, f"Score {job['match_score']} must be between 1 and 10"
        assert "matching_skills" in job
        assert "missing_skills" in job
        assert "rationale" in job
        assert "application_tip" in job
    print("PASS: Scoring engine validated ratings out of 10.")


def test_api_endpoints():
    client = TestClient(app)

    # 1. Config endpoint
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "has_gemini_key" in data
    print("PASS: GET /api/config returned valid status.")

    # 2. Sample CV endpoint
    resp = client.get("/api/sample-cv")
    assert resp.status_code == 200
    data = resp.json()
    assert "Alex Turner" in data["content"]
    print("PASS: GET /api/sample-cv returned sample content.")

    # 3. Match Jobs endpoint with CV text
    resp = client.post("/api/match-jobs", data={
        "cv_text": data["content"],
        "target_location": "United Kingdom",
        "min_score": "5.0"
    })
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["success"] is True
    assert len(res_data["jobs"]) > 0
    top_job = res_data["jobs"][0]
    print(f"PASS: POST /api/match-jobs matched {len(res_data['jobs'])} jobs. Top Match: {top_job['title']} (Score: {top_job['match_score']}/10).")


def test_tailor_application():
    client = TestClient(app)
    sample_path = BASE_DIR / "sample_cv.txt"
    with open(sample_path, "r", encoding="utf-8") as f:
        cv_text = f.read()

    selected_jobs = [
        {
            "id": "job-1",
            "title": "Senior Service Delivery Manager",
            "company": "NEST Corporation",
            "location": "London, UK",
            "tags": ["ITIL", "ServiceNow", "SLA Delivery"],
            "description": "Lead enterprise IT service delivery, major incident management, and ITIL operations."
        },
        {
            "id": "job-2",
            "title": "Service Delivery Manager",
            "company": "CMC Markets",
            "location": "London, UK",
            "tags": ["Incident Management", "Problem Management", "Change Management"],
            "description": "Manage multi-vendor services, SLA compliance, and CAB governance."
        },
        {
            "id": "job-3",
            "title": "IT Operations Lead",
            "company": "Mitimes Solutions",
            "location": "London, UK",
            "tags": ["ITSM", "Cloud Operations", "Continuous Improvement"],
            "description": "Drive IT operational excellence and 24/7 service availability."
        }
    ]

    resp = client.post("/api/tailor-application", json={
        "cv_text": cv_text,
        "selected_jobs": selected_jobs
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "applications" in data and len(data["applications"]) == 3

    # Verify per-job CVs and cover letters
    for idx, app_pkg in enumerate(data["applications"]):
        assert "tailored_cv" in app_pkg and len(app_pkg["tailored_cv"]) > 50, f"App {idx} must have tailored CV"
        assert "cover_letter" in app_pkg and len(app_pkg["cover_letter"]) > 50, f"App {idx} must have cover letter"
        assert "target_skills_highlighted" in app_pkg and len(app_pkg["target_skills_highlighted"]) > 0, f"App {idx} must have target skills"
        # Verify job-specific skills are highlighted
        if app_pkg["company"] == "NEST Corporation":
            assert any("ITIL" in s or "ServiceNow" in s or "SLA" in s for s in app_pkg["target_skills_highlighted"])
            assert "NEST Corporation" in app_pkg["cover_letter"]

    print(f"PASS: POST /api/tailor-application created {len(data['applications'])} individual, spec-tailored CVs and cover letters.")


def test_pdf_download():
    client = TestClient(app)

    # 1. Test CV PDF Generation
    cv_req = {
        "doc_type": "cv",
        "content_text": "# Alex Turner\n\nSenior Software Engineer\n\n## SUMMARY\nExperienced engineer specializing in cloud architectures and Python.\n\n## CORE SKILLS\n- Python, FastAPI, Docker, PostgreSQL\n\n## EXPERIENCE\n### Lead Engineer - Tech Corp (2020 - Present)\n- Built microservices serving 1M daily requests.\n- Reduced cloud infrastructure costs by 30%.",
        "candidate_name": "Alex Turner",
        "target_role": "Senior Cloud Engineer",
        "target_company": "Acme Cloud UK",
        "key_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"]
    }
    resp = client.post("/api/download-cv-pdf", json=cv_req)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF"), "Generated file must have %PDF header"
    assert len(resp.content) > 1000, "PDF must not be empty"
    print("PASS: POST /api/download-cv-pdf returned formatted CV PDF.")

    # 2. Test Cover Letter PDF Generation
    cl_req = {
        "doc_type": "cover_letter",
        "content_text": "Dear Hiring Manager,\n\nI am writing to express my strong interest in the Senior Cloud Engineer position at Acme Cloud UK.\n\nWith extensive experience in Python, FastAPI, and Docker, I have delivered resilient cloud solutions.\n\nThank you for considering my application.\n\nSincerely,\nAlex Turner",
        "candidate_name": "Alex Turner",
        "target_role": "Senior Cloud Engineer",
        "target_company": "Acme Cloud UK"
    }
    resp = client.post("/api/download-cv-pdf", json=cl_req)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    print("PASS: POST /api/download-cv-pdf returned formatted Cover Letter PDF.")


if __name__ == "__main__":
    print("--- Running UK JobMatch AI Test Suite ---")
    test_cv_parser()
    test_job_aggregation()
    test_heuristic_scoring()
    test_api_endpoints()
    test_tailor_application()
    test_pdf_download()
    print("ALL TESTS PASSED SUCCESSFULLY!")
