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


def extract_contact_line(lines: List[str]) -> str:
    """Extracts clean location, email, phone, and LinkedIn info from candidate CV header lines."""
    contact_items = []
    for l in lines[1:6]:
        clean = l.replace("#", "").strip()
        if clean.isupper() or len(clean) > 130 or len(clean) < 5:
            continue
        if any(w in clean.lower() for w in ["summary", "profile", "experienced", "engineer with", "manager with", "results-driven"]):
            continue
        if any(marker in clean.lower() for marker in ["@", "+44", "+", "linkedin.com", "github.com", "tel:", "phone:"]) or (
            any(loc in clean.lower() for loc in ["london", "manchester", "birmingham", "leeds", "uk", "united kingdom", "remote"]) and ("|" in clean or "," in clean)
        ):
            contact_items.append(clean)
    return "  •  ".join(contact_items) if contact_items else "United Kingdom"


def parse_and_clean_cv_experience(cv_text: str) -> Dict[str, str]:
    """
    Parses original CV text into clean experience and education sections.
    Preserves all real roles, past employers, dates, and bullet points.
    """
    lines = [l.strip() for l in cv_text.splitlines() if l.strip()]
    experience_lines = []
    education_lines = []
    current_sec = "other"

    for line in lines:
        clean_upper = line.replace("#", "").strip().upper()
        if any(h in clean_upper for h in ["EXPERIENCE", "WORK HISTORY", "EMPLOYMENT HISTORY", "CAREER HISTORY"]):
            current_sec = "experience"
            continue
        elif any(h in clean_upper for h in ["EDUCATION", "CERTIFICATIONS", "QUALIFICATIONS", "ACADEMIC BACKGROUND"]):
            current_sec = "education"
            continue
        elif any(h in clean_upper for h in ["SUMMARY", "PROFILE", "CORE SKILLS", "TECHNICAL SKILLS"]):
            current_sec = "other"
            continue

        if current_sec == "experience":
            if "|" in line and not line.startswith("-") and not line.startswith("*") and not line.startswith("•"):
                experience_lines.append(f"### {line}")
            elif re.search(r"\b(19\d\d|20\d\d)\b", line) and ("-" in line or "–" in line or "present" in line.lower()) and not line.startswith("-") and not line.startswith("•"):
                experience_lines.append(f"*{line}*")
            else:
                experience_lines.append(line)
        elif current_sec == "education":
            education_lines.append(line)

    if not experience_lines:
        experience_lines = [l for l in lines[10:] if not any(w in l.lower() for w in ["education", "certification", "degree"])]
    if not education_lines:
        education_lines = [
            "- Relevant Professional Qualifications & Industry Certifications aligned with UK standards."
        ]

    return {
        "experience": "\n".join(experience_lines),
        "education": "\n".join(education_lines)
    }


def tailor_single_job_fallback(cv_text: str, job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic fallback generator for an individual job specification.
    Produces a submission-ready, executive UK CV (with ZERO references to the prospective employer)
    and a bespoke, spec-focused cover letter citing exact required skills.
    """
    lines = [l.strip() for l in cv_text.splitlines() if l.strip()]
    name = lines[0] if lines else "Candidate Name"
    name = name.replace("#", "").strip()
    if "|" in name:
        name = name.split("|")[0].strip()

    title = job.get("title", "Target Role")
    company = job.get("company", "Target Company")
    location = job.get("location", "United Kingdom")
    salary = job.get("salary", "Competitive")
    tags = job.get("tags", [])

    if not tags:
        tags = ["Service Delivery", "Operations Management", "Stakeholder Leadership"]

    tags_str = ", ".join(tags[:6])
    primary_skills = ", ".join(tags[:3])

    contact_line = extract_contact_line(lines)
    parsed_sections = parse_and_clean_cv_experience(cv_text)

    # 1. Spec-Tailored CV (100% Submission Ready, ZERO prospective company mentions)
    tailored_cv = f"""# {name}
**{title}**
{contact_line}

---

## PROFESSIONAL SUMMARY
Accomplished, results-oriented **{title}** with an established track record of delivering operational excellence, strategic governance, and technical alignment across mission-critical enterprise environments. Brings deep expertise across **{tags_str}**, with a demonstrated ability to optimize complex workflows, drive continual service improvement, and achieve outstanding SLA reliability. Skilled at collaborating with cross-functional leadership, steering multi-stakeholder initiatives, and translating strategic business priorities into robust, high-availability operational execution.

---

## CORE COMPETENCIES & TECHNICAL EXPERTISE
- **Role Specialisms & Target Competencies:** {tags_str}
- **Operational Governance & Reliability:** ITIL Framework, SLA/OLA Delivery, Incident & Problem Resolution, Root Cause Analysis, Change Advisory Board (CAB)
- **Technical Architecture & Systems:** Cloud Infrastructure, System Reliability, Process Automation, System Monitoring, Risk Mitigation
- **Leadership & Stakeholder Alignment:** Vendor & Contract Management, Multi-Vendor Governance, Continual Service Improvement (CSI), Cross-Functional Leadership

---

## PROFESSIONAL EXPERIENCE

{parsed_sections['experience']}

---

## EDUCATION & PROFESSIONAL CERTIFICATIONS

{parsed_sections['education']}
"""

    # 2. Spec-Focused Cover Letter (Specifically citing and addressing the hiring team at the company)
    cover_letter = f"""{name}
{contact_line.split('•')[0].strip() if '•' in contact_line else 'United Kingdom'}

Date: {job.get('posted_date') or 'Current Application'}

Hiring Team
{company}
{location}

Subject: Application for {title} - {name}

Dear Hiring Team at {company},

I am writing to express my enthusiastic interest in the {title} vacancy at {company}. Having thoroughly reviewed your job specification, I was particularly drawn to your emphasis on {tags_str}. With a proven career founded on disciplined execution, stakeholder alignment, and operational excellence, I am confident that my background directly addresses the priorities and challenges of this role.

In reviewing your requirements, I noted the critical need for hands-on leadership in {primary_skills}. Throughout my commercial experience, I have spearheaded initiatives that demanded these exact competencies—establishing robust governance models, resolving complex operational bottlenecks, and ensuring multi-stakeholder SLA compliance. My background in orchestrating cross-functional teams and managing enterprise-grade service delivery equips me to immediately contribute to {company}'s ongoing success.

Furthermore, the core responsibilities outlined in your vacancy—ranging from proactive incident mitigation to stakeholder relationship management—strongly resonate with my leadership methodology. I approach every operational challenge with a focus on measurable business impact, transparency, and continual service improvement.

I would welcome the opportunity to discuss how my tailored expertise in {tags_str} can support {company}'s strategic goals. Thank you for your time and consideration, and I look forward to hearing from you.

Yours sincerely,

{name}
"""

    key_amendments = [
        f"Re-aligned Professional Summary and headline specifically for the {title} domain.",
        f"Elevated target competencies ({tags_str}) to the top of Core Competencies.",
        f"Structured experience to highlight governance, SLAs, and technical requirements matching {title}.",
        f"Drafted bespoke UK cover letter directly addressing {company}'s {title} specification."
    ]

    return {
        "job_id": job.get("id", f"job-{title}"),
        "job_title": title,
        "company": company,
        "location": location,
        "salary": salary,
        "target_skills_highlighted": tags[:6],
        "key_amendments": key_amendments,
        "tailored_cv": tailored_cv.strip(),
        "cover_letter": cover_letter.strip()
    }



def tailor_single_job_gemini(
    cv_text: str,
    job: Dict[str, Any],
    client: genai.Client
) -> Optional[Dict[str, Any]]:
    """
    Uses Gemini LLM Agent to tailor a CV and generate a bespoke, spec-focused cover letter
    for a single job specification.
    Strictly forbids prospective employer mentions in the CV body and header.
    """
    title = job.get("title", "Target Role")
    company = job.get("company", "Target Company")
    location = job.get("location", "United Kingdom")
    salary = job.get("salary", "Competitive")
    tags = job.get("tags", [])
    desc = job.get("description", "")[:1200]

    prompt = f"""You are an elite UK Executive Career Consultant, ATS Optimization Specialist, and Senior Recruitment Director.
Your task is to tailor the candidate's CV specifically for the role of "{title}".
You will also write a bespoke, spec-focused UK cover letter for the hiring team at "{company}".

CRITICAL INSTRUCTIONS FOR CV ("tailored_cv"):
1. STRICTLY NO MENTION OF THE PROSPECTIVE COMPANY ("{company}") IN THE CV:
   - A professional CV is an independent personal career document.
   - It must NEVER mention "{company}", "applying to {company}", or "tailored for {company}" anywhere in the text, header, summary, or bullets.
   - The prospective company name "{company}" belongs EXCLUSIVELY in the Cover Letter.
2. PROFESSIONAL ROLE ALIGNMENT:
   - Set the candidate's header headline to "{title}" (or matching seniority/domain).
   - This positions the candidate directly as a qualified, experienced specialist in this field.
3. EXECUTIVE PROFESSIONAL SUMMARY:
   - Craft a compelling, punchy 3-4 sentence professional summary highlighting their total years of experience, core domain authority, and proven track record delivering the exact outcomes required by a {title}.
   - Seamlessly weave in the primary methodologies, technologies, and governance standards requested in the job description ({', '.join(tags)}) without referencing any prospective employer name.
4. CATEGORIZED CORE COMPETENCIES:
   - Reorganize and elevate skills so that the specific skills requested in the job specification ({', '.join(tags)}) are front and center in categorized, bulleted groups (e.g., Core Specialisms, Technical & Tools, Leadership & Governance).
5. REFINED WORK EXPERIENCE:
   - Re-frame and elevate the candidate's actual work history achievements using strong executive action verbs (e.g., Spearheaded, Architected, Orchestrated, Optimized, Delivered, Championed).
   - Draw attention to achievements, metrics (%, £, SLAs, latency, scale), and tools that prove candidate competence in the job's key requirements.
   - Keep all past employer names, past job titles, and dates 100% factually aligned with the candidate's real CV.
   - Format each role cleanly with:
     ### Job Title | Company Name | Location
     *Date Range*
     - Action-oriented bullet point with quantifiable impact
6. READY-TO-SUBMIT FORMAT:
   - Output clean, professional Markdown that can immediately be exported to PDF or submitted directly to an ATS.
   - Standard UK sections:
     # [Candidate Name]
     **{title}**
     [Location] | [Email] | [Phone] | [LinkedIn]
     
     ---
     ## PROFESSIONAL SUMMARY
     [3-4 sentences of executive positioning]
     
     ---
     ## CORE COMPETENCIES & TECHNICAL EXPERTISE
     - **[Category 1 (Spec Focus)]:** [Skills requested in spec]
     - **[Category 2]:** [Technical skills / Tools]
     - **[Category 3]:** [Governance, Delivery, Leadership]
     
     ---
     ## PROFESSIONAL EXPERIENCE
     ### [Job Title] | [Past Company] | [Location]
     *[Start Date] – [End Date]*
     - [Quantified achievement bullet point]
     ...
     
     ---
     ## EDUCATION & CERTIFICATIONS
     - [Degrees, certifications, etc.]

CRITICAL INSTRUCTIONS FOR COVER LETTER ("cover_letter"):
- The cover letter IS where {company} and {title} are explicitly addressed.
- Address formally to "Hiring Team at {company}".
- Paragraph 1: Enthusiastic opening specifying application for {title} at {company}.
- Paragraph 2: Direct evidence of candidate's commercial achievements in the specific technical and operational skills requested ({', '.join(tags)}).
- Paragraph 3: Connect candidate's proven methodologies to the responsibilities and challenges described in the job spec.
- Paragraph 4: Formal, confident closing and call to interview.
- Sign off: "Yours sincerely,\n[Candidate Name]".

TARGET JOB SPECIFICATION:
- Title: {title}
- Company: {company}
- Location: {location}
- Salary: {salary}
- Stated Skills / Tags: {', '.join(tags)}
- Job Description & Responsibilities:
\"\"\"
{desc}
\"\"\"

CANDIDATE ORIGINAL CV:
\"\"\"
{cv_text[:6000]}
\"\"\"

Return ONLY a valid JSON object with this exact structure:
{{
  "target_skills_highlighted": ["Skill1", "Skill2", "Skill3"],
  "key_amendments": [
    "Realigned Professional Summary and headline specifically for the {title} domain",
    "Elevated [Key Tool] and [Key Skill] to top of Core Competencies",
    "Quantified achievements in [Area] to showcase relevant scale and impact"
  ],
  "tailored_cv": "# Full Name\\n**{title}**\\n...",
  "cover_letter": "Dear Hiring Team at {company}..."
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
            logger.info(f"Successfully tailored application for {company} using {model_name}.")

            raw_cv = data.get("tailored_cv", "").strip()

            # Safety post-processing: remove prospective company from CV header if accidentally present
            sanitized_cv = re.sub(
                rf"\*\*(?:Target Role:)?\s*{re.escape(title)}\s*\|\s*{re.escape(company)}\*\*",
                f"**{title}**",
                raw_cv,
                flags=re.IGNORECASE
            )
            sanitized_cv = re.sub(
                rf"\b(?:specifically tailored for|specifically for|tailored specifically for)\s+(?:the\s+)?(?:position\s+at\s+)?{re.escape(company)}\b",
                "for this role",
                sanitized_cv,
                flags=re.IGNORECASE
            )
            sanitized_cv = re.sub(
                rf"\b(?:exceed organizational SLA commitments for|contribute to)\s+{re.escape(company)}\b",
                "exceed organizational SLA commitments",
                sanitized_cv,
                flags=re.IGNORECASE
            )

            return {
                "job_id": job.get("id", f"job-{title}"),
                "job_title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "target_skills_highlighted": data.get("target_skills_highlighted", tags[:6]),
                "key_amendments": data.get("key_amendments", []),
                "tailored_cv": sanitized_cv,
                "cover_letter": data.get("cover_letter", "").strip()
            }
        except Exception as e:
            logger.warning(f"Gemini tailoring for {company} with {model_name} failed: {e}. Trying next option...")

    return None


def tailor_cv_and_cover_letter(
    cv_text: str,
    selected_jobs: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Master function:
    Creates an INDIVIDUAL tailored CV and a SPEC-FOCUSED cover letter for EACH selected job (up to 3).
    Each CV specifically brings forward the skills most needed for that job requirement.
    """
    if not selected_jobs:
        return {"success": False, "error": "No jobs selected for tailoring."}

    client = get_gemini_client(api_key)
    applications = []
    any_ai_powered = False

    for job in selected_jobs[:3]:
        app_package = None
        if client:
            app_package = tailor_single_job_gemini(cv_text, job, client)
            if app_package:
                any_ai_powered = True

        # Fallback if client is None or Gemini call failed
        if not app_package:
            app_package = tailor_single_job_fallback(cv_text, job)

        applications.append(app_package)

    # Legacy compatibility fields for top-level consumers
    primary_app = applications[0] if applications else {}
    legacy_cover_letters = [
        {
            "job_id": app["job_id"],
            "job_title": app["job_title"],
            "company": app["company"],
            "recipient": f"Hiring Team at {app['company']}",
            "content": app["cover_letter"]
        }
        for app in applications
    ]

    return {
        "success": True,
        "ai_powered": any_ai_powered,
        "applications": applications,
        # Legacy backward-compatible fields:
        "tailored_cv": primary_app.get("tailored_cv", ""),
        "key_amendments": primary_app.get("key_amendments", []),
        "cover_letters": legacy_cover_letters
    }
