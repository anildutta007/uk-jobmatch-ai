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


if __name__ == "__main__":
    print("--- Running UK JobMatch AI Test Suite ---")
    test_cv_parser()
    test_job_aggregation()
    test_heuristic_scoring()
    test_api_endpoints()
    print("ALL TESTS PASSED SUCCESSFULLY!")
