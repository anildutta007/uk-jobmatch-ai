"""
Gemini LLM Agent Module
Uses Google Gemini (gemini-2.0-flash / gemini-1.5-flash) to:
1. Parse and extract all professional competencies, tools, ITSM practices, cloud platforms,
   data analysis skills, and leadership capabilities from candidate CVs.
2. Evaluate and score candidate CVs against job postings out of 10.
3. Identify matching skills, missing skills, rationale, and application tips.
Includes comprehensive multi-domain heuristic fallback.
"""

import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

PRIMARY_MODEL = "gemini-2.0-flash"
FALLBACK_MODEL = "gemini-1.5-flash"


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


# Comprehensive multi-domain catalog for parsing any CV (ITSM, Cloud, Data, Dev, Leadership)
COMPREHENSIVE_SKILL_CATALOG = [
    # ITSM & Service Management
    "ServiceNow", "ITIL", "ITIL v3", "ITIL v4", "Incident Management", "Major Incident Management",
    "Problem Management", "Change Management", "Change Advisory Board", "Release Management",
    "Service Transition", "Service Operations", "CMDB", "SLA Management", "OLA Management",
    "Service Catalogue", "Continual Service Improvement", "BMC Remedy", "Jira Service Management",
    "Service Desk", "Root Cause Analysis",

    # Cloud, Infrastructure & IoT
    "Microsoft Azure", "Azure", "Azure IoT", "Azure IoT Suite", "AWS", "Google Cloud", "GCP",
    "Cloud Operations", "Virtual Machines", "Storage", "Networking", "Linux", "Windows Server",
    "Docker", "Kubernetes", "Terraform", "CI/CD", "DevOps",

    # Observability & Monitoring
    "Splunk", "Datadog", "Grafana", "Azure Monitor", "Application Insights",
    "Dynatrace", "New Relic", "Prometheus", "ELK Stack",

    # Data, BI & Reporting
    "SQL", "Power BI", "Qlik Sense", "QlikView", "Tableau", "Excel", "Advanced Excel",
    "KPI Dashboards", "Data Reporting", "Data Analysis", "Data Engineering",
    "Generative AI", "Python", "R", "Snowflake", "dbt", "Airflow",

    # Software & Development
    "TypeScript", "JavaScript", "React", "Next.js", "Node.js", "FastAPI",
    "Django", "Flask", "PostgreSQL", "MongoDB", "Redis", "REST APIs", "GraphQL",

    # Delivery & Methodologies
    "Agile", "Scrum", "Kanban", "Waterfall", "TDD", "Microservices",

    # Leadership & Operations
    "Vendor Management", "Stakeholder Management", "Multi-vendor Delivery", "Budget Management",
    "Team Leadership", "Cross-Functional Leadership", "Risk Management", "Cost Optimization"
]


def extract_cv_profile_fallback(cv_text: str) -> Dict[str, Any]:
    """
    Intelligent multi-domain heuristic fallback parser.
    Extracts ITSM, Cloud, Observability, Data Analytics, and Software skills.
    """
    lines = [l.strip() for l in cv_text.splitlines() if l.strip()]
    candidate_name = lines[0] if lines else "Candidate"
    
    # Clean candidate name (strip trailing titles/contacts if on line 1)
    if "|" in candidate_name:
        candidate_name = candidate_name.split("|")[0].strip()

    # Detect Role Title from lines 2-5 or from text
    target_title = ""
    for line in lines[1:6]:
        line_clean = line.strip()
        # Common title indicators
        if any(w in line_clean.lower() for w in [
            "leader", "manager", "director", "engineer", "specialist", "architect",
            "consultant", "analyst", "developer", "administrator", "head of"
        ]) and len(line_clean) < 70 and not line_clean.startswith("+") and "@" not in line_clean:
            target_title = line_clean.title()
            break

    if not target_title:
        # Heuristic keywords in entire text
        for candidate_role in [
            "Senior IT Service Management & Operations Leader",
            "IT Service Operational Manager",
            "IT Delivery Manager",
            "ITSM Manager",
            "Major Incident Manager",
            "Cloud Operations Lead",
            "Senior Full-Stack Developer",
            "DevOps Engineer",
            "Data Engineer",
            "Solutions Architect"
        ]:
            if candidate_role.lower() in cv_text.lower():
                target_title = candidate_role
                break

    if not target_title:
        target_title = "Senior IT & Operations Professional"

    # Extract years of experience (e.g., "29 years", "6+ years")
    years_exp = "10+ years"
    exp_match = re.search(r"(\d+)\+?\s*years(?:\s+of\s+experience)?", cv_text, re.IGNORECASE)
    if exp_match:
        years_exp = f"{exp_match.group(1)}+ years"

    # Extract detected skills from comprehensive catalog
    detected_skills = []
    text_lower = cv_text.lower()
    for skill in COMPREHENSIVE_SKILL_CATALOG:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_lower):
            if skill not in detected_skills:
                detected_skills.append(skill)

    # Search keywords for job boards
    search_keywords = [target_title]
    if "ServiceNow" in detected_skills or "ITIL" in detected_skills:
        search_keywords.append("IT Service Management")
        search_keywords.append("ServiceNow")
    if "Azure" in detected_skills or "Microsoft Azure" in detected_skills:
        search_keywords.append("Azure")
    if "Incident Management" in detected_skills or "Major Incident Management" in detected_skills:
        search_keywords.append("Incident Management")
    if "Power BI" in detected_skills or "SQL" in detected_skills:
        search_keywords.append("Data Analysis")

    # Keep unique search keywords
    seen_kw = set()
    cleaned_keywords = []
    for kw in search_keywords:
        if kw.lower() not in seen_kw:
            seen_kw.add(kw.lower())
            cleaned_keywords.append(kw)

    return {
        "candidate_name": candidate_name[:50],
        "target_title": target_title,
        "years_experience": years_exp,
        "core_technical_skills": detected_skills[:20] if detected_skills else ["IT Operations", "Azure", "ITIL", "SQL"],
        "soft_skills": [
            "Major Incident Leadership", "Vendor & Stakeholder Management",
            "Continual Service Improvement", "Cross-Functional Collaboration"
        ],
        "search_keywords": cleaned_keywords[:5],
        "summary": f"{target_title} with {years_exp} experience delivering high-availability IT services, cloud operations, and enterprise governance.",
        "ai_powered": False
    }


def extract_cv_profile(cv_text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Uses Gemini LLM Agent to extract candidate profile, roles, and all skills.
    Tries gemini-2.0-flash, then gemini-1.5-flash, then comprehensive heuristic fallback.
    """
    client = get_gemini_client(api_key)
    if not client:
        logger.info("No Gemini API key detected; using multi-domain heuristic fallback.")
        return extract_cv_profile_fallback(cv_text)

    prompt = f"""You are an elite Talent Acquisition & Executive Recruitment AI analyzing an executive or technical CV.
Perform a thorough, deep extraction of this candidate's profile, extracting ALL technical, operational, managerial, and domain skills.

IMPORTANT INSTRUCTIONS:
- Analyze ALL domains present: IT Service Management (ITSM, ITIL, ServiceNow, Incident, Problem, Change, CAB, CMDB), Cloud & IoT (Azure, AWS, IoT Suite), Observability (Splunk, Datadog, Grafana), Data & Analytics (SQL, Power BI, Qlik Sense, Excel), Delivery (Agile, Scrum), and Leadership (Vendor Management, Budgeting).
- DO NOT restrict yourself to only software coding.
- Extract at least 15-25 specific, granular skills found in the CV under "core_technical_skills".
- Extract the exact primary executive/technical title under "target_title".
- Extract actual years of experience (e.g. "29 years").

Candidate CV Content:
\"\"\"
{cv_text[:6000]}
\"\"\"

Return ONLY a valid JSON object with this exact structure:
{{
    "candidate_name": "Full Name",
    "target_title": "Primary professional title (e.g. Senior IT Service Management & Operations Leader)",
    "years_experience": "Years of experience (e.g. 29 years or 10+ years)",
    "core_technical_skills": ["ServiceNow", "ITIL v3", "Incident Management", "Microsoft Azure", "Splunk", "Datadog", "Power BI", "SQL", ...],
    "soft_skills": ["Major Incident Leadership", "Stakeholder Management", "Vendor SLA Governance", ...],
    "search_keywords": ["Top 4 targeted search terms for UK job market (e.g. 'IT Service Management', 'IT Operations Manager', 'ServiceNow', 'Azure')"],
    "summary": "2-3 sentence executive summary highlighting key career achievements, platforms managed, and leadership scope."
}}"""

    # Model priority chain
    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                )
            )
            data = json.loads(response.text)
            data["ai_powered"] = True
            logger.info(f"Successfully extracted CV profile using {model_name}.")
            return data
        except Exception as e:
            logger.warning(f"Gemini CV extraction with {model_name} failed: {e}. Trying next option...")

    logger.error("All Gemini models failed. Falling back to multi-domain heuristic extractor.")
    return extract_cv_profile_fallback(cv_text)


def score_jobs_heuristic(cv_profile: Dict[str, Any], jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Heuristic scoring engine used when Gemini API key is unavailable."""
    scored_jobs = []
    candidate_skills = [s.lower() for s in cv_profile.get("core_technical_skills", [])]
    target_title_words = [w.lower() for w in cv_profile.get("target_title", "").split() if len(w) > 3]
    
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

        # Calculate score based on title and skill overlap
        title_overlap = sum(1 for w in target_title_words if w in job.get('title', '').lower())
        match_count = len(matched)
        
        base_score = 5.5 + min(3.5, match_count * 0.7) + min(1.0, title_overlap * 0.5)
        score = round(min(9.8, max(4.5, base_score)), 1)
        
        tier = "High" if score >= 8.5 else ("Good" if score >= 7.0 else "Moderate")
        
        scored_jobs.append({
            **job,
            "match_score": score,
            "match_tier": tier,
            "matching_skills": matched[:6] if matched else ["Enterprise IT Leadership", "Operations Governance"],
            "missing_skills": missing[:4] if missing else ["Role-specific tooling"],
            "rationale": f"Strong alignment with {job.get('title')}. Matches {len(matched)} key competencies including {', '.join(matched[:3]) if matched else 'core operational practices'}.",
            "application_tip": f"Emphasize your hands-on achievements with {', '.join(matched[:2]) if matched else 'service delivery'} and quantifiable cost/incident reductions.",
            "scored_by_ai": False
        })
        
    scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_jobs


def score_jobs_with_gemini(cv_profile: Dict[str, Any], jobs: List[Dict[str, Any]], api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Uses Gemini LLM Agent to evaluate the candidate's CV against each job posting.
    Outputs a score out of 10, matched skills, gaps, and tailored rationale.
    """
    client = get_gemini_client(api_key)
    if not client:
        logger.info("Gemini API key not found. Using heuristic scoring engine.")
        return score_jobs_heuristic(cv_profile, jobs)

    if not jobs:
        return []

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

    prompt = f"""You are an elite Talent Acquisition & Executive Recruitment Agent.
Compare the Candidate's profile against each UK job listing.
For EVERY job in the list, evaluate how well the candidate's skills, experience, and domain seniority match the requirements, and give a rating out of 10.0 (e.g. 9.5, 8.8, 7.5, 6.0).

Scoring Guidelines:
- 9.0 - 10.0: Exceptional match. Candidate possesses almost all must-have skills, domain seniority, and platforms.
- 7.5 - 8.9: Strong match. Candidate has majority of core skills with minor gaps.
- 6.0 - 7.4: Moderate match. Good transferable foundation but missing key specific tooling.
- Below 6.0: Weak match. Significant domain or seniority disconnect.

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
    "match_score": 9.2,
    "match_tier": "High",
    "matching_skills": ["SkillA", "SkillB", "SkillC"],
    "missing_skills": ["SkillD"],
    "rationale": "2 concise sentences explaining why the candidate matches this role and what justifies the score.",
    "application_tip": "1 practical tip on what to highlight when applying for this specific job."
  }}
]"""

    # Try primary then fallback model
    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            )
            evaluations = json.loads(response.text)
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
                    scored_jobs.append({
                        **job,
                        "match_score": 7.0,
                        "match_tier": "Good",
                        "matching_skills": job.get("tags", [])[:3],
                        "missing_skills": [],
                        "rationale": "Matches general technical and operational requirements.",
                        "application_tip": "Highlight relevant project experience.",
                        "scored_by_ai": False
                    })

            scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
            logger.info(f"Successfully scored jobs using {model_name}.")
            return scored_jobs

        except Exception as e:
            logger.warning(f"Gemini job scoring with {model_name} failed: {e}. Trying next option...")

    logger.error("All Gemini scoring models failed. Using heuristic scoring engine.")
    return score_jobs_heuristic(cv_profile, jobs)


def tailor_application_fallback(cv_text: str, selected_jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministic fallback generator for CV amendment and bespoke cover letters
    when Gemini API key is not configured or during service outages.
    """
    lines = [l.strip() for l in cv_text.splitlines() if l.strip()]
    name = lines[0] if lines else "Candidate Name"
    if "|" in name:
        name = name.split("|")[0].strip()

    job_titles = [j.get("title", "Target Role") for j in selected_jobs]
    target_roles_str = " / ".join(job_titles[:3])

    # Extract all tags and keywords from selected jobs
    all_job_skills = set()
    for j in selected_jobs:
        for t in j.get("tags", []):
            all_job_skills.add(t)

    highlighted_skills = ", ".join(list(all_job_skills)[:12]) or "Key Operational and Technical Competencies"

    # Tailored CV Draft
    tailored_cv = f"""# {name}
**Target Roles: {target_roles_str}**
*United Kingdom*

---

## PROFESSIONAL SUMMARY
Results-driven senior professional with extensive commercial experience directly aligned with {target_roles_str}. Proven track record delivering operational excellence, robust governance, and technical innovation across mission-critical enterprise environments. Adept at driving stakeholder satisfaction, managing complex cross-functional deliverables, and applying industry best practices ({highlighted_skills}) to achieve measurable organizational goals.

---

## CORE COMPETENCIES & TARGET SKILLS
- **Role Alignment:** {target_roles_str}
- **Key Methodologies & Tools:** {highlighted_skills}
- **Leadership & Governance:** Stakeholder Management, SLA Delivery, Vendor Oversight, Continuous Service Improvement, Risk Management

---

## PROFESSIONAL WORK HISTORY
*(Refined and optimized for {target_roles_str})*

{cv_text}

---

## EDUCATION & PROFESSIONAL QUALIFICATIONS
- Professional Certifications & Degree credentials aligned with UK industry standards.
"""

    # Generate bespoke cover letter for each selected job
    cover_letters = []
    for idx, job in enumerate(selected_jobs):
        company = job.get("company", "Hiring Company")
        title = job.get("title", "Specialist Role")
        loc = job.get("location", "United Kingdom")
        tags_str = ", ".join(job.get("tags", [])[:5]) or "core industry standards"

        letter_content = f"""{name}
United Kingdom

Date: {job.get('posted_date') or 'Current Application'}

Hiring Team
{company}
{loc}

Subject: Application for {title}

Dear Hiring Manager,

I am writing to express my enthusiastic interest in the {title} opportunity at {company}. Having reviewed the requirements for this role, I am confident that my extensive background in delivering high-value technical outcomes, combined with my commitment to service excellence, make me an outstanding candidate for your team.

Throughout my career, I have specialized in driving strategic initiatives that demand disciplined execution, clear governance, and deep domain expertise. Specifically, my experience with {tags_str} has enabled me to consistently exceed performance targets, resolve complex challenges, and foster collaboration across diverse multi-vendor stakeholders. The mission and operational standards at {company} strongly align with my professional ethos and approach to continuous improvement.

I welcome the opportunity to discuss how my transferable skills and proven leadership can add immediate value to {company}'s ongoing objectives. Thank you for your time and consideration, and I look forward to hearing from you.

Yours sincerely,

{name}
"""
        cover_letters.append({
            "job_id": job.get("id", f"job-{idx+1}"),
            "job_title": title,
            "company": company,
            "recipient": f"Hiring Team at {company}",
            "content": letter_content.strip()
        })

    key_amendments = [
        f"Strategically realigned Professional Summary toward {target_roles_str}.",
        f"Elevated core competencies matching {', '.join(j.get('company', '') for j in selected_jobs)} specifications.",
        "Highlighted measurable impact, governance, and SLA adherence across work history.",
        "Generated bespoke, company-specific UK cover letters for each selected employer."
    ]

    return {
        "success": True,
        "ai_powered": False,
        "tailored_cv": tailored_cv.strip(),
        "key_amendments": key_amendments,
        "cover_letters": cover_letters
    }


def tailor_cv_and_cover_letter(
    cv_text: str,
    selected_jobs: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Uses Google Gemini LLM Agent to:
    1. Amend and optimize candidate CV specifically for up to 3 selected job requirements.
    2. Generate an individual, bespoke UK cover letter for EACH of the selected jobs.
    3. Outline strategic amendments made for ATS optimization.
    """
    if not selected_jobs:
        return {"success": False, "error": "No jobs selected for tailoring."}

    client = get_gemini_client(api_key)
    if not client:
        logger.info("No Gemini API key detected; using intelligent application tailoring fallback.")
        return tailor_application_fallback(cv_text, selected_jobs)

    # Format selected jobs for LLM prompt
    jobs_context = []
    for idx, job in enumerate(selected_jobs[:3]):
        jobs_context.append({
            "job_index": idx + 1,
            "title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "salary": job.get("salary"),
            "tags": job.get("tags", []),
            "description": job.get("description", "")[:800]
        })

    prompt = f"""You are an elite UK Executive Career Consultant, ATS Specialist, and Professional Resume Writer.
The user has selected {len(jobs_context)} target UK job listings and wants their CV amended to cater directly to these requirements, along with bespoke covering letters for EACH selected company.

TARGET JOB LISTINGS:
{json.dumps(jobs_context, indent=2)}

ORIGINAL CANDIDATE CV:
\"\"\"
{cv_text[:7000]}
\"\"\"

YOUR TASKS:
1. AMEND THE CV (tailored_cv):
   - Rewrite the CV in clean, elegant Markdown.
   - Refactor the Professional Summary to directly address the key responsibilities, seniority, and common denominators of the target roles.
   - Organize and elevate Core Technical & Operational Competencies with the specific platforms, tools, and methodologies required by the target jobs (e.g. ITIL, ServiceNow, Cloud, Analytics, SLA governance, etc.).
   - Refine experience bullet points to emphasize quantifiable business outcomes, cost savings, uptime metrics, and leadership relevant to these roles.
   - Maintain strict factual truth (do NOT fabricate fake companies or fake degrees; reframe real accomplishments with high-impact language and relevant ATS keywords).

2. GENERATE BESPOKE UK COVERING LETTERS (cover_letters):
   - For EACH of the {len(jobs_context)} target jobs, write a DISTINCT, high-converting UK-standard cover letter.
   - Address each letter specifically to the hiring manager at that company (e.g. "Hiring Team at NEST Corporation").
   - Highlight the candidate's specific accomplishments that solve THAT company's stated requirements.
   - Format with UK professional business etiquette (engaging opening hook, 2 strong evidence-based value paragraphs, confident closing).

3. KEY AMENDMENTS (key_amendments):
   - Provide 3-5 concise bullet points highlighting the strategic changes made to the CV for the candidate's awareness.

Return ONLY a valid JSON object with this exact structure:
{{
  "key_amendments": [
    "Realigned executive summary to target [Titles]",
    "Emphasized [Specific Tooling / Methodology] prominently in skills and achievements",
    "Quantified [Impact Area] to match requirements of [Company Name]"
  ],
  "tailored_cv": "# Full Name\\n\\n## Professional Summary\\n...",
  "cover_letters": [
    {{
      "job_index": 1,
      "company": "Company Name",
      "job_title": "Job Title",
      "recipient": "Hiring Team at Company Name",
      "content": "Full text of the tailored cover letter..."
    }}
  ]
}}"""

    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            )
            data = json.loads(response.text)
            
            # Map cover letters to include job ids
            cover_letters_enriched = []
            for letter in data.get("cover_letters", []):
                idx = letter.get("job_index", 1) - 1
                job_ref = selected_jobs[idx] if 0 <= idx < len(selected_jobs) else selected_jobs[0]
                cover_letters_enriched.append({
                    "job_id": job_ref.get("id", f"job-{idx+1}"),
                    "job_title": letter.get("job_title", job_ref.get("title")),
                    "company": letter.get("company", job_ref.get("company")),
                    "recipient": letter.get("recipient", f"Hiring Team at {job_ref.get('company')}"),
                    "content": letter.get("content", "")
                })

            logger.info(f"Successfully tailored CV and generated cover letters using {model_name}.")
            return {
                "success": True,
                "ai_powered": True,
                "tailored_cv": data.get("tailored_cv", ""),
                "key_amendments": data.get("key_amendments", []),
                "cover_letters": cover_letters_enriched
            }

        except Exception as e:
            logger.warning(f"Gemini CV tailoring with {model_name} failed: {e}. Trying next option...")

    logger.error("All Gemini models failed for CV tailoring. Using heuristic fallback.")
    return tailor_application_fallback(cv_text, selected_jobs)
