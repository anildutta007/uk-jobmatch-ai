"""
Gemini LLM Agent Module
Uses Google Gemini (gemini-2.5-flash) to:
1. Parse and extract key skills, titles, and competencies from candidate CVs.
2. Evaluate and score candidate CVs against job postings out of 10.
3. Identify matching skills, missing skills, rationale, and application tips.
Includes graceful heuristic fallback when no API key is present.
"""

import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"


def get_gemini_client(api_key: Optional[str] = None) -> Optional[genai.Client]:
    """Retrieves an initialized Gemini Client if API key is available."""
    key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "your_gemini_api_key_here":
        return None
    try:
        return genai.Client(api_key=key)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini Client: {e}")
        return None


def extract_cv_profile_fallback(cv_text: str) -> Dict[str, Any]:
    """Heuristic fallback parser when Gemini API key is not configured."""
    text_lower = cv_text.lower()
    
    # Common tech skills dictionary
    tech_catalog = [
        "python", "javascript", "typescript", "react", "next.js", "vue", "angular",
        "node.js", "fastapi", "django", "flask", "docker", "kubernetes", "aws",
        "gcp", "azure", "sql", "postgresql", "mongodb", "redis", "graphql", "rest",
        "ci/cd", "terraform", "linux", "git", "c++", "c#", ".net", "java", "spring"
    ]
    detected_skills = [skill.title() for skill in tech_catalog if re.search(r"\b" + re.escape(skill) + r"\b", text_lower)]
    
    # Extract candidate name (usually on the first non-empty line)
    lines = [l.strip() for l in cv_text.splitlines() if l.strip()]
    candidate_name = lines[0] if lines else "Candidate"
    
    # Role heuristic
    role = "Software Engineer"
    for title in ["Senior Full-Stack Developer", "Full-Stack Engineer", "Backend Developer", "Frontend Developer", "DevOps Engineer", "Data Engineer"]:
        if title.lower() in text_lower:
            role = title
            break

    return {
        "candidate_name": candidate_name[:50],
        "target_title": role,
        "years_experience": "5+ years",
        "core_technical_skills": detected_skills[:12] if detected_skills else ["Python", "JavaScript", "SQL", "Cloud"],
        "soft_skills": ["Problem Solving", "Team Leadership", "Agile Communication"],
        "search_keywords": [role, detected_skills[0] if detected_skills else "Python", "React", "AWS"],
        "summary": "Experienced professional with background in software development and modern technologies.",
        "ai_powered": False
    }


def extract_cv_profile(cv_text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Uses Gemini LLM Agent to extract candidate profile, roles, and skills.
    """
    client = get_gemini_client(api_key)
    if not client:
        logger.info("No Gemini API key detected; using heuristic fallback for profile extraction.")
        return extract_cv_profile_fallback(cv_text)

    prompt = f"""You are an expert HR and recruitment AI agent analyzing a candidate's CV.
Extract key professional attributes into a valid JSON object.

Candidate CV Content:
\"\"\"
{cv_text[:4000]}
\"\"\"

Return ONLY a JSON object with this exact structure:
{{
    "candidate_name": "Full name or Candidate",
    "target_title": "Primary professional title (e.g. Senior Full-Stack Developer)",
    "years_experience": "Estimated years of experience (e.g. 6+ years)",
    "core_technical_skills": ["Skill1", "Skill2", "Skill3", ...],
    "soft_skills": ["Communication", "Leadership", ...],
    "search_keywords": ["Top 3-4 keywords to search jobs in UK (e.g. 'Full Stack Developer', 'Python', 'React')"],
    "summary": "A 2-sentence summary of the candidate's core strengths and career focus.",
    "ai_powered": true
}}"""

    try:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            )
        )
        data = json.loads(response.text)
        data["ai_powered"] = True
        return data
    except Exception as e:
        logger.error(f"Gemini CV extraction failed: {e}. Falling back to heuristic.")
        fallback = extract_cv_profile_fallback(cv_text)
        fallback["error"] = str(e)
        return fallback


def score_jobs_heuristic(cv_profile: Dict[str, Any], jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Heuristic scoring engine used when Gemini API key is not yet provided."""
    scored_jobs = []
    candidate_skills = [s.lower() for s in cv_profile.get("core_technical_skills", [])]
    
    for job in jobs:
        job_text = f"{job.get('title', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()
        matched = []
        missing = []
        
        # Check matched skills
        for s in candidate_skills:
            if s in job_text:
                matched.append(s.title())

        # Check job tags for missing skills
        for tag in job.get("tags", []):
            if tag.lower() not in candidate_skills and tag.title() not in matched:
                missing.append(tag.title())

        match_count = len(matched)
        base_score = 5.0 + min(4.5, match_count * 0.9)
        score = round(min(9.8, max(4.0, base_score)), 1)
        
        tier = "High" if score >= 8.0 else ("Good" if score >= 6.5 else "Moderate")
        
        scored_jobs.append({
            **job,
            "match_score": score,
            "match_tier": tier,
            "matching_skills": matched[:6] if matched else ["Transferable Engineering Skills"],
            "missing_skills": missing[:4] if missing else ["Role-specific tooling"],
            "rationale": f"Strong alignment with {job.get('title')} requirements. Matched {len(matched)} core competencies including {', '.join(matched[:3]) if matched else 'general experience'}.",
            "application_tip": f"Highlight your hands-on experience with {', '.join(matched[:2]) if matched else 'core tools'} and relevant project outcomes.",
            "scored_by_ai": False
        })
        
    scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_jobs


def score_jobs_with_gemini(cv_profile: Dict[str, Any], jobs: List[Dict[str, Any]], api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Uses Gemini LLM Agent to rigorously compare the candidate's CV against each job posting.
    Outputs a score out of 10, matched skills, gaps, and tailored rationale.
    """
    client = get_gemini_client(api_key)
    if not client:
        logger.info("Gemini API key not found. Using heuristic scoring engine.")
        return score_jobs_heuristic(cv_profile, jobs)

    if not jobs:
        return []

    # Compact job representations to save tokens and minimize latency
    jobs_summary = []
    for idx, job in enumerate(jobs):
        jobs_summary.append({
            "index": idx,
            "id": job.get("id"),
            "title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "tags": job.get("tags", []),
            "description_snippet": job.get("description", "")[:500]
        })

    prompt = f"""You are an elite Talent Acquisition & AI Matching Agent.
Compare the Candidate's profile against each UK job listing.
For EVERY job in the list, evaluate how well the candidate's skills and experience match the job requirements, and give a score out of 10.0 (e.g. 9.4, 8.2, 7.0, 5.5).

Scoring Guidelines:
- 9.0 - 10.0: Exceptional match. Candidate possesses almost all must-have skills and relevant seniority.
- 7.5 - 8.9: Strong match. Candidate has majority of core skills with minor gaps that can be easily learned.
- 6.0 - 7.4: Moderate match. Good transferable foundation but missing key specific frameworks/technologies.
- Below 6.0: Weak match. Significant domain or technology disconnect.

Candidate Profile:
- Name: {cv_profile.get('candidate_name')}
- Target Title: {cv_profile.get('target_title')}
- Experience: {cv_profile.get('years_experience')}
- Core Skills: {', '.join(cv_profile.get('core_technical_skills', []))}
- Summary: {cv_profile.get('summary')}

Job Listings to evaluate:
{json.dumps(jobs_summary, indent=2)}

Return ONLY a valid JSON array of objects with the exact format:
[
  {{
    "index": 0,
    "match_score": 8.8,
    "match_tier": "High",
    "matching_skills": ["SkillA", "SkillB"],
    "missing_skills": ["SkillC"],
    "rationale": "2 concise sentences explaining why the candidate matches this role and what justifies the score.",
    "application_tip": "1 practical tip on what to highlight when applying for this specific job."
  }}
]"""

    try:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            )
        )
        evaluations = json.loads(response.text)
        
        # Merge Gemini evaluations back into the original job items
        eval_dict = {item.get("index"): item for item in evaluations if isinstance(item, dict)}
        
        scored_jobs = []
        for idx, job in enumerate(jobs):
            eval_data = eval_dict.get(idx)
            if eval_data:
                score = round(float(eval_data.get("match_score", 7.0)), 1)
                scored_jobs.append({
                    **job,
                    "match_score": score,
                    "match_tier": eval_data.get("match_tier", "Good"),
                    "matching_skills": eval_data.get("matching_skills", []),
                    "missing_skills": eval_data.get("missing_skills", []),
                    "rationale": eval_data.get("rationale", "Good alignment with candidate profile."),
                    "application_tip": eval_data.get("application_tip", "Tailor your application to highlight relevant projects."),
                    "scored_by_ai": True
                })
            else:
                # Fallback for any unindexed item
                scored_jobs.append({
                    **job,
                    "match_score": 7.0,
                    "match_tier": "Good",
                    "matching_skills": job.get("tags", [])[:3],
                    "missing_skills": [],
                    "rationale": "Matches general technical requirements.",
                    "application_tip": "Highlight relevant project experience.",
                    "scored_by_ai": False
                })

        # Sort descending by match score
        scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
        return scored_jobs

    except Exception as e:
        logger.error(f"Gemini batch scoring failed: {e}. Falling back to heuristic.")
        return score_jobs_heuristic(cv_profile, jobs)
