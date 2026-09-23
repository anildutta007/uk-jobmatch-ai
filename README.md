# UK JobMatch AI - Gemini-Powered Job Search & Scoring Agent

A modern, cost-optimized web-based application targeted at the **UK job market**. Users upload their CV (PDF, DOCX, or TXT), and an intelligent Google Gemini LLM agent extracts their skills, aggregates relevant live UK job listings, and scores each job out of 10 with matched skills, skill gaps, and interview application tips.

---

## Key Features

- **CV Parsing**: Supports `.pdf`, `.docx`, and `.txt` resumes.
- **UK Market Focus**: Aggregates opportunities across London, Manchester, Birmingham, Edinburgh, Bristol, and UK-eligible remote positions.
- **Gemini LLM Agent**: Uses Google Gemini 2.5 Flash to evaluate role alignment, matching competencies, and gaps.
- **Strict Scoring out of 10**: Every job receives a calibrated rating (e.g., `9.4 / 10`) along with a transparent rationale.
- **Zero Cost Architecture**:
  - Leverages free public job aggregator APIs (Arbeitnow, Remotive, Jobicy) requiring zero credit cards and zero paid subscriptions.
  - Leverages Google AI Studio's free tier for Gemini Flash.
  - Two-stage local pre-filtering reduces LLM token consumption by over 80%.
- **Local .env Configuration**: API keys are securely loaded from a local `.env` file.

---

## Quick Start

### 1. Configure Your Gemini API Key
Open `.env` in the project root:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Get a free key from [Google AI Studio](https://aistudio.google.com/)).*

> Note: If no key is set yet, the application automatically runs in a smart heuristic fallback mode so you can test all features immediately. You can also save your key directly in the web browser settings!

### 2. Run the Application
Double-click `run.bat` or run:
```bash
python -m uvicorn backend.main:app --port 8000 --reload
```
Then open your browser at **`http://localhost:8000`**.

### 3. Test with 1 Click
Click **"Load Sample Senior Full-Stack CV"** in the web app, choose your location preference, and click **"Find & Score Matching Jobs"**.

---

## Project Structure

```
Anil Google Projects/
├── backend/
│   ├── cv_parser.py       # PDF, DOCX, TXT document parser
│   ├── job_services.py    # UK job aggregators & local cost-optimization filter
│   ├── gemini_agent.py    # Gemini Flash LLM profile extraction & deep scoring
│   └── main.py            # FastAPI server & static file host
├── frontend/
│   ├── index.html         # Modern Tailwind UI with live progress animations
│   ├── styles.css         # Custom animations & step styles
│   └── app.js             # Client application logic & card renderer
├── sample_cv.txt          # Pre-loaded sample UK CV for instant testing
├── requirements.txt       # Python dependencies
├── .env                   # Local configuration & API keys
├── .env.example           # Environment template
└── run.bat                # 1-click Windows startup script
```
