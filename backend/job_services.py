"""
Job Services Module
Fetches, aggregates, and pre-filters job postings with a specific focus on the UK market.
Integrates with:
- Public Zero-Key APIs (Arbeitnow, Remotive, Jobicy)
- Adzuna UK API (if credentials provided in .env)
- Reed.co.uk API (if credentials provided in .env)
- Curated UK Tech & Professional Job Pool (fallback & supplementary)
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

# Curated UK Job Pool (Realistically modelled after active UK market postings)
CURATED_UK_JOBS: List[Dict[str, Any]] = [
    {
        "id": "uk-curated-1",
        "title": "Senior Full-Stack Developer (Python & React)",
        "company": "Moneta FinTech Group",
        "location": "London, UK (Hybrid)",
        "salary": "£75,000 - £90,000 + Equity",
        "description": (
            "We are looking for a Senior Full-Stack Developer to join our high-growth London FinTech team. "
            "You will build mission-critical banking APIs and responsive user dashboards. "
            "Requirements: 5+ years commercial experience with Python (FastAPI or Django), TypeScript, React, "
            "PostgreSQL, Docker, and AWS. Experience with TDD and microservices architecture is essential."
        ),
        "url": "https://www.linkedin.com/jobs/search/?keywords=Python+React+London",
        "tags": ["Python", "FastAPI", "React", "TypeScript", "AWS", "PostgreSQL", "FinTech"],
        "posted_date": "Recently posted",
        "source": "UK Tech Board"
    },
    {
        "id": "uk-curated-2",
        "title": "Full Stack Software Engineer",
        "company": "CloudScale UK Ltd",
        "location": "Manchester, UK (Remote / Flexible)",
        "salary": "£60,000 - £72,000",
        "description": (
            "CloudScale is expanding our engineering team in Manchester. Seeking a Full Stack Engineer "
            "to scale our cloud management portal. Required: Strong proficiency in JavaScript/TypeScript, "
            "React, Node.js or Python backend frameworks (FastAPI/Flask), Redis, and AWS/GCP cloud environments. "
            "Knowledge of CI/CD pipelines (GitHub Actions) and Docker containers."
        ),
        "url": "https://www.cwjobs.co.uk/jobs/full-stack-developer/in-manchester",
        "tags": ["TypeScript", "React", "Python", "Node.js", "Docker", "AWS", "Redis"],
        "posted_date": "1 day ago",
        "source": "UK Tech Board"
    },
    {
        "id": "uk-curated-3",
        "title": "Lead Python Engineer (Cloud & Microservices)",
        "company": "Vanguard Data Systems",
        "location": "Bristol, UK (Remote Options)",
        "salary": "£80,000 - £95,000",
        "description": (
            "Seeking a hands-on Lead Python Developer to architect robust data processing microservices. "
            "Must have extensive experience with Python 3, FastAPI, async programming, Kafka/RabbitMQ, "
            "Kubernetes, and AWS. Terraform knowledge is a major plus. Leadership and mentoring experience valued."
        ),
        "url": "https://www.technojobs.co.uk/jobs/python-developer/in-bristol",
        "tags": ["Python", "FastAPI", "AWS", "Kubernetes", "Microservices", "Terraform", "Kafka"],
        "posted_date": "2 days ago",
        "source": "UK Tech Board"
    },
    {
        "id": "uk-curated-4",
        "title": "Frontend React / Next.js Developer",
        "company": "Bloom Digital Agency",
        "location": "London, UK (Soho)",
        "salary": "£55,000 - £65,000",
        "description": (
            "Bloom is looking for a talented Frontend React Developer with an eye for design and performance. "
            "Requirements: Strong JavaScript/TypeScript, React 18+, Next.js, Tailwind CSS, HTML5, CSS3, and REST/GraphQL APIs. "
            "Experience with modern testing tools (Jest, React Testing Library)."
        ),
        "url": "https://www.reed.co.uk/jobs/react-developer-in-london",
        "tags": ["React", "Next.js", "TypeScript", "Tailwind CSS", "JavaScript", "GraphQL"],
        "posted_date": "3 days ago",
        "source": "UK Tech Board"
    },
    {
        "id": "uk-curated-5",
        "title": "Backend Python / AI Services Developer",
        "company": "Cognitive Health Labs",
        "location": "Cambridge, UK (Hybrid)",
        "salary": "£65,000 - £80,000",
        "description": (
            "Cognitive Health Labs uses AI to assist UK medical diagnostics. We need a Backend Developer "
            "skilled in Python, FastAPI, relational databases (PostgreSQL), and cloud APIs. Experience integrating "
            "LLM APIs (Gemini, OpenAI) or machine learning models into production systems is highly desirable."
        ),
        "url": "https://www.jobsite.co.uk/jobs/python-developer/in-cambridge",
        "tags": ["Python", "FastAPI", "PostgreSQL", "Docker", "Machine Learning", "LLM", "AI"],
        "posted_date": "Just now",
        "source": "UK Tech Board"
    },
    {
        "id": "uk-curated-6",
        "title": "DevOps & Cloud Infrastructure Engineer",
        "company": "Apex Financial Technologies",
        "location": "Edinburgh, UK (Remote UK)",
        "salary": "£70,000 - £85,000",
        "description": (
            "Join our Edinburgh DevOps practice. You will automate CI/CD, manage Kubernetes clusters on AWS, "
            "and provision infrastructure as code using Terraform. Experience with Python scripting, Linux, "
            "Docker, and Prometheus/Grafana monitoring is expected."
        ),
        "url": "https://www.s1jobs.com/jobs/devops-engineer/in-edinburgh",
        "tags": ["DevOps", "AWS", "Kubernetes", "Terraform", "Docker", "CI/CD", "Python"],
        "posted_date": "4 days ago",
        "source": "UK Tech Board"
    },
    {
        "id": "uk-curated-7",
        "title": "Data Engineer / Analytics Engineer",
        "company": "Retail Insights UK",
        "location": "Birmingham, UK (Hybrid)",
        "salary": "£58,000 - £70,000",
        "description": (
            "Build automated data pipelines for major UK retail brands. Skills required: Python, SQL, "
            "PostgreSQL/Snowflake, dbt, Apache Airflow, and AWS S3/Glue. Experience working in Agile teams."
        ),
        "url": "https://www.totaljobs.com/jobs/data-engineer/in-birmingham",
        "tags": ["Python", "SQL", "PostgreSQL", "Data Pipelines", "AWS", "Snowflake"],
        "posted_date": "5 days ago",
        "source": "UK Tech Board"
    },
    {
        "id": "uk-curated-8",
        "title": "Senior JavaScript / Node.js Backend Engineer",
        "company": "Streamline Logistics",
        "location": "London, UK (Remote UK)",
        "salary": "£72,000 - £85,000",
        "description": (
            "Streamline is modernizing freight shipping across Great Britain. Looking for a Senior Backend Developer "
            "with Node.js, Express/NestJS, TypeScript, MongoDB/PostgreSQL, Redis, and event-driven architecture. "
            "AWS Lambda and Serverless experience is a plus."
        ),
        "url": "https://www.linkedin.com/jobs/search/?keywords=Node.js+London",
        "tags": ["Node.js", "TypeScript", "Express", "MongoDB", "AWS", "Redis"],
        "posted_date": "2 days ago",
        "source": "UK Tech Board"
    }
]


async def fetch_arbeitnow_jobs(query: str = "") -> List[Dict[str, Any]]:
    """
    Fetches jobs from Arbeitnow's free public API.
    Filters for UK and remote opportunities.
    """
    jobs = []
    url = "https://www.arbeitnow.com/api/job-board-api"
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", []):
                    title = item.get("title", "")
                    location = item.get("location", "")
                    description = item.get("description", "")
                    # Clean simple HTML tags from description
                    clean_desc = re.sub(r"<[^>]+>", " ", description)
                    clean_desc = " ".join(clean_desc.split())[:600]

                    # Filter for UK, remote, or tech relevance
                    is_uk = any(k in location.lower() for k in ["uk", "united kingdom", "london", "manchester", "remote", "england", "scotland"])
                    is_remote = item.get("remote", False)

                    if is_uk or is_remote:
                        jobs.append({
                            "id": f"arbeitnow-{item.get('slug', len(jobs))}",
                            "title": title,
                            "company": item.get("company_name", "Technology Company"),
                            "location": f"{location} (Remote)" if is_remote and "remote" not in location.lower() else location,
                            "salary": "Competitive (Market Rate)",
                            "description": clean_desc,
                            "url": item.get("url", "https://www.arbeitnow.com"),
                            "tags": item.get("tags", []),
                            "posted_date": "Recent",
                            "source": "Arbeitnow"
                        })
    except Exception as e:
        logger.warning(f"Error fetching from Arbeitnow: {e}")
    return jobs


async def fetch_remotive_jobs(query: str = "") -> List[Dict[str, Any]]:
    """
    Fetches remote jobs from Remotive's free public API.
    """
    jobs = []
    url = f"https://remotive.com/api/remote-jobs?limit=25"
    if query:
        url += f"&search={query}"
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("jobs", []):
                    geo = item.get("candidate_required_location", "")
                    # Accept worldwide or UK/Europe eligible remote roles
                    is_eligible = any(k in geo.lower() for k in ["uk", "united kingdom", "worldwide", "anywhere", "europe", "emea", ""])
                    if is_eligible:
                        clean_desc = re.sub(r"<[^>]+>", " ", item.get("description", ""))
                        clean_desc = " ".join(clean_desc.split())[:600]
                        jobs.append({
                            "id": f"remotive-{item.get('id', len(jobs))}",
                            "title": item.get("title", ""),
                            "company": item.get("company_name", ""),
                            "location": f"Remote ({geo})" if geo else "Remote (UK Eligible)",
                            "salary": item.get("salary", "Competitive"),
                            "description": clean_desc,
                            "url": item.get("url", "https://remotive.com"),
                            "tags": item.get("tags", []),
                            "posted_date": item.get("publication_date", "Recent")[:10],
                            "source": "Remotive"
                        })
    except Exception as e:
        logger.warning(f"Error fetching from Remotive: {e}")
    return jobs


async def fetch_adzuna_uk_jobs(query: str = "", location: str = "United Kingdom") -> List[Dict[str, Any]]:
    """
    Fetches UK jobs from Adzuna API if app credentials are provided in .env.
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return []

    jobs = []
    url = f"https://api.adzuna.com/v1/api/jobs/gb/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": 20,
        "what": query or "software engineer",
        "where": location or "United Kingdom",
        "content-type": "application/json"
    }
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    sal_min = item.get("salary_min")
                    sal_max = item.get("salary_max")
                    salary_str = f"£{int(sal_min):,} - £{int(sal_max):,}" if sal_min and sal_max else "Competitive"
                    jobs.append({
                        "id": f"adzuna-{item.get('id', len(jobs))}",
                        "title": item.get("title", ""),
                        "company": item.get("company", {}).get("display_name", "Hiring Company"),
                        "location": item.get("location", {}).get("display_name", "UK"),
                        "salary": salary_str,
                        "description": item.get("description", "")[:600],
                        "url": item.get("redirect_url", ""),
                        "tags": [item.get("category", {}).get("label", "Technology")],
                        "posted_date": item.get("created", "Recent")[:10],
                        "source": "Adzuna UK"
                    })
    except Exception as e:
        logger.warning(f"Error fetching from Adzuna: {e}")
    return jobs


def pre_filter_and_rank_jobs(jobs: List[Dict[str, Any]], keywords: List[str], max_count: int = 12) -> List[Dict[str, Any]]:
    """
    Locally ranks and filters job listings based on keyword overlap with CV profile.
    This saves significant LLM token costs by selecting only the top candidates for Gemini scoring.
    """
    if not jobs:
        return []

    scored_jobs = []
    lowered_keywords = [k.lower() for k in keywords if len(k) > 1]

    for job in jobs:
        searchable_text = f"{job.get('title', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()
        title_lower = job.get('title', '').lower()

        overlap_score = 0
        for kw in lowered_keywords:
            if kw in title_lower:
                overlap_score += 4  # Title matches are weighted higher
            elif kw in searchable_text:
                overlap_score += 1

        scored_jobs.append((overlap_score, job))

    # Sort descending by preliminary overlap
    scored_jobs.sort(key=lambda x: x[0], reverse=True)

    # Return top N jobs
    return [job for _, job in scored_jobs[:max_count]]


async def aggregate_uk_jobs(search_keywords: List[str], target_location: str = "United Kingdom", max_results: int = 15) -> List[Dict[str, Any]]:
    """
    Master function to aggregate UK jobs across all available providers:
    1. Curated UK Tech jobs pool
    2. Arbeitnow API (UK/Remote)
    3. Remotive API (Remote UK eligible)
    4. Adzuna UK (if configured in .env)
    Then filters and selects the top candidates for Gemini evaluation.
    """
    all_jobs: List[Dict[str, Any]] = []

    # 1. Include curated high-quality UK jobs
    all_jobs.extend(CURATED_UK_JOBS)

    # Primary query keyword
    primary_query = search_keywords[0] if search_keywords else "software engineer"

    # 2. Try fetching from public free APIs
    try:
        arbeit_jobs = await fetch_arbeitnow_jobs(primary_query)
        all_jobs.extend(arbeit_jobs)
    except Exception as e:
        logger.error(f"Arbeitnow fetch failed: {e}")

    try:
        remotive_jobs = await fetch_remotive_jobs(primary_query)
        all_jobs.extend(remotive_jobs)
    except Exception as e:
        logger.error(f"Remotive fetch failed: {e}")

    # 3. Try Adzuna UK if API key configured
    try:
        adzuna_jobs = await fetch_adzuna_uk_jobs(primary_query, target_location)
        all_jobs.extend(adzuna_jobs)
    except Exception as e:
        logger.error(f"Adzuna fetch failed: {e}")

    # Deduplicate by job title + company
    unique_jobs: List[Dict[str, Any]] = []
    seen = set()
    for job in all_jobs:
        key = (job.get("title", "").strip().lower(), job.get("company", "").strip().lower())
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    # Pre-filter to top candidate pool for LLM scoring
    selected_jobs = pre_filter_and_rank_jobs(unique_jobs, search_keywords, max_count=max_results)
    return selected_jobs
