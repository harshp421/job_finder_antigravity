# 🚀 Antigravity Autonomous Job Search & Application Platform

An end-to-end autonomous pipeline that finds remote software engineering jobs across **LinkedIn, Indeed, Glassdoor, and direct ATS portals (Greenhouse, Lever)**, matches them against your experience using AI, and automates form filling.

---

## 🛠️ Architecture

```
job_finder/
├── config/
│   ├── profile.yaml          # Your master profile, skills, salary, and QA rules
│   └── settings.py           # Pydantic schema validation
├── database/
│   ├── models.py             # SQLite schemas for jobs, applications, answers
│   └── db.py                 # DB queries & state management
├── harvesters/
│   ├── base.py               # Abstract base harvester interface
│   ├── greenhouse_harvester.py # Greenhouse public API scraper (high quality, zero ban risk)
│   ├── lever_harvester.py    # Lever public API scraper
│   └── jobspy_harvester.py   # LinkedIn, Indeed, Glassdoor scraper
├── agents/
│   ├── matcher.py            # AI semantic matching & scoring engine (0-100)
│   ├── answer_agent.py       # Dynamic question answering agent for ATS forms
│   └── appliers/
│       ├── base_applier.py   # Base class for application execution
│       ├── greenhouse_applier.py # Automated Greenhouse form submitter
│       └── lever_applier.py  # Automated Lever form submitter
├── tracker/
│   └── crm.py                # Rich terminal dashboard, stats & application audit history
├── main.py                   # Master CLI entry point
└── data/
    ├── job_pipeline.db       # SQLite local database
    └── screenshots/          # Audit screenshots of filled forms and confirmations
```

---

## ⚡ Quickstart

### 1. Configure Your Profile
Edit `config/profile.yaml` with your details:
- Contact information (Email, Phone, LinkedIn, GitHub).
- Tech stack & years of experience.
- Target roles and salary expectations.
- Place your PDF resume in `resumes/` and specify the path in `config/profile.yaml`.

### 2. Run Commands

#### 🔥 The One Single Command (End-to-End Autonomous Pipeline):
Run the entire loop in one single command: finds jobs, evaluates match scores, generates tailored ATS PDF resumes, applies on company career sites, and sends email outreach via Gmail:
```bash
# Dry-run preview mode (fills forms with screenshots and emails previews to your inbox):
python main.py run

# Live submission mode (submits directly to company portals and live emails):
python main.py run --live

# Target specific startup hubs (e.g. Dubai, Singapore, India, Global):
python main.py run --region dubai --limit 5
```

---

#### Individual Pipeline Stages (Optional):


#### Score & Match Jobs:
```bash
# Evaluate all unscored jobs against your profile (only queues matches >= 75%)
python main.py match --min-score 75
```

#### Generate Role- & Country-Tailored ATS Resume:
```bash
# Generate tailored PDF resume for top queued job or specific Job ID:
python main.py resume --job-id 5f2d929c549d770e

# Output PDF saved to resumes/Harsh_Parmar_{Company}_{ID}.pdf
```

#### Send Application Email via Gmail:
```bash
# Preview mode (sends customized pitch + attached PDF to your Gmail inbox):
python main.py email --job-id 5f2d929c549d770e

# Live mode (sends directly to company/recruiter email):
python main.py email --job-id 5f2d929c549d770e --to careers@tamara.co --live
```

#### Auto-Apply on Company Career Sites:
```bash
# Dry run: fills the form, attaches tailored resume, and captures preview screenshot
python main.py apply --job-id 5f2d929c549d770e

# Live submit: submits the application on the company site
python main.py apply --job-id 5f2d929c549d770e --live
```

#### Check Status & Dashboard:
```bash
python main.py status
```

#### Run All (Autonomous Pipeline):
```bash
# Runs Harvest -> Match -> Dynamic Resume -> Dry-Run Apply -> Dashboard
python main.py run-all --region dubai
```

---

## 🛡️ Anti-Bot & Account Safety
- **Direct ATS endpoints (Greenhouse / Lever)** do not require logins or credentials, eliminating any risk of account restrictions.
- **Safety Cap**: Daily applications are capped to avoid triggering velocity checks.
- **Preview First**: The system defaults to `dry-run` mode so you can inspect filled screenshots in `data/screenshots/` before enabling live submission.
