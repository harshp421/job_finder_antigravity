import re
import html
from pathlib import Path
from typing import Dict, Any, List, Optional
from config.settings import CandidateProfile, load_profile
from database.db import update_job_resume

class ResumeBuilder:
    """
    Builds dynamic, ATS-compliant, role-and-country-tailored PDF resumes
    using Playwright headless rendering from semantic HTML/CSS templates.
    """

    def __init__(self, profile: Optional[CandidateProfile] = None):
        self.profile = profile or load_profile()
        self.resumes_dir = Path(__file__).parent.parent / "resumes"
        self.resumes_dir.mkdir(parents=True, exist_ok=True)

    def analyze_role_and_region(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze job title, description, location, and company to determine
        the optimal resume framing, target title, highlights, and regional adaptations.
        """
        title = (job_data.get("title") or "").lower()
        desc = (job_data.get("description") or "").lower()
        loc = (job_data.get("location") or "").lower()
        company = job_data.get("company", "")

        # 1. Determine Role Archetype
        is_frontend = any(k in title for k in ["frontend", "front-end", "ui", "ux", "design system", "web", "react", "client"])
        is_backend = any(k in title for k in ["backend", "back-end", "python", "ruby", "distributed", "platform", "system", "infrastructure", "cloud", "ai engineering", "agent"])
        is_fullstack = any(k in title for k in ["fullstack", "full stack", "full-stack", "sde", "software engineer", "developer", "product engineer"])

        if is_frontend and not is_backend:
            role_type = "frontend"
            tailored_title = "Senior Frontend & Design Systems Engineer"
        elif is_backend and not is_frontend:
            role_type = "backend"
            tailored_title = "Senior Backend & Distributed Systems Engineer"
        else:
            role_type = "fullstack"
            tailored_title = "Software Development Engineer (Full Stack & Systems)"

        # 2. Determine Regional Customization
        is_dubai = any(k in loc for k in ["dubai", "uae", "emirates", "abu dhabi", "riyadh", "saudi", "middle east", "mena"])
        is_singapore = any(k in loc for k in ["singapore", "sg", "apac", "southeast asia"])
        is_india = any(k in loc for k in ["india", "bengaluru", "bangalore", "delhi", "mumbai", "hyderabad", "pune", "ahmedabad", "remote india"])
        is_remote_global = any(k in loc for k in ["remote", "worldwide", "united states", "us", "uk", "europe", "emea", "canada"])

        if is_dubai:
            region_badge = "Ahmedabad, India (Immediate Relocation to Dubai/UAE & GCC | Fast-Track Onboarding)"
            regional_summary_note = (
                f"Equipped with enterprise-grade platform engineering experience (including environmental monitoring reports for NEOM and low-code decision automation engines), "
                f"readily prepared to deliver high-impact engineering in the {company} team with complete regional and timezone alignment."
            )
        elif is_singapore:
            region_badge = "Ahmedabad, India (Available for Relocation to Singapore / APAC Timezone Alignment)"
            regional_summary_note = (
                f"Experienced in scaling high-throughput distributed workflows and developer tooling, "
                f"eager to bring robust systems engineering and rapid execution to {company}'s APAC and global operations."
            )
        elif is_india:
            region_badge = "Ahmedabad, Gujarat, India (Immediate / 2-Week Notice Period | Remote or Hybrid)"
            regional_summary_note = (
                f"High-ownership engineer with a track record of cutting infrastructure overhead and scaling concurrent execution engines 4x; "
                f"available to drive zero-to-one and scaled systems at {company} immediately."
            )
        else:
            region_badge = "Remote Worldwide (Synchronous with US & EMEA Working Hours)"
            regional_summary_note = (
                f"Proven track record working asynchronously with US-incorporated startups (AAVIL Inc, Delaware), "
                f"championing strict international engineering standards (W3C DTCG tokens, WebAssembly WASI isolation, sub-40KB bundle architectures)."
            )

        # 3. Dynamic Summary Crafting
        if role_type == "frontend":
            summary = (
                f"Specialist Frontend & Design Systems Engineer with deep expertise in modern web performance, platform-native Light-DOM web components, and universal component architectures. "
                f"Creator of NNUI-KIT (nnuikit.com), an open-source 45-component Light-DOM architecture bundling under 38.9 kB gzipped with native form serialization (ElementInternals) and cross-tab synchronization (BroadcastChannel). "
                f"At Oizom, built the company-wide design system (30+ components) reducing UI delivery time by 50-80% and slashing page load times by 75%. {regional_summary_note}"
            )
        elif role_type == "backend":
            summary = (
                f"Backend & Systems Engineer specializing in distributed workflow orchestration, database scaling, and sandboxed execution environments. "
                f"At AAVIL Inc, architected the core server-authoritative DAG scheduling engine for the Decision Intelligence Platform, scaling concurrent execution capacity from 20 to 80+ runners via PgBouncer pooling, and isolated custom Python scripts using WebAssembly (WASI CPython). "
                f"At Oizom, architected an IoT device management system scaling data ingestion 100x (1,000 to 100,000 rows) with zero memory leaks. {regional_summary_note}"
            )
        else:
            summary = (
                f"Passionate Full Stack Developer (SDE 2) with 3+ years experience shipping mission-critical systems, from low-code decision orchestration platforms to open-source UI component systems. "
                f"Own the server-authoritative DAG workflow engine at AAVIL Inc scaling concurrent execution to 80+ runners with PgBouncer connection pooling and WebAssembly (WASI) sandboxing. "
                f"Architect of NNUI-KIT (nnuikit.com), a 45-component Light-DOM suite bundling under 38.9 kB. {regional_summary_note}"
            )

        return {
            "role_type": role_type,
            "tailored_title": tailored_title,
            "region_badge": region_badge,
            "summary": summary
        }

    def generate_html(self, job_data: Dict[str, Any]) -> str:
        """
        Generate semantic, ATS-optimized HTML resume for the target job.
        """
        meta = self.analyze_role_and_region(job_data)
        pi = self.profile.personal_info
        ts = self.profile.tech_stack
        role_type = meta["role_type"]

        # Filter and prioritize project highlights according to role type
        projects = self.profile.projects or []
        sorted_projects = []
        if role_type == "frontend":
            sorted_projects = sorted(projects, key=lambda p: 0 if "nnui" in p.name.lower() else (1 if "oizom" in p.name.lower() else 2))
        elif role_type == "backend":
            sorted_projects = sorted(projects, key=lambda p: 0 if "decision" in p.name.lower() else (1 if "kred" in p.name.lower() else 2))
        else:
            sorted_projects = projects

        # Skills categories
        lang_str = ", ".join(ts.primary_languages)
        fw_str = ", ".join(ts.frameworks_and_libraries[:14])
        sys_str = ", ".join(ts.systems_and_architecture[:10])
        db_str = ", ".join(ts.databases_and_cloud[:12])

        # Experience items
        exp_blocks = []
        for exp in self.profile.experience_highlights:
            highlights_html = "".join([f"<li>{html.escape(h)}</li>" for h in exp.highlights[:5]])
            exp_blocks.append(f"""
            <div class="job-entry">
                <div class="job-header">
                    <div>
                        <span class="job-company">{html.escape(exp.company)}</span>
                        <span class="job-role"> — {html.escape(exp.role)}</span>
                    </div>
                    <span class="job-duration">{html.escape(exp.duration)}</span>
                </div>
                <ul class="bullet-list">
                    {highlights_html}
                </ul>
            </div>
            """)

        # Projects items
        proj_blocks = []
        for proj in sorted_projects[:3]:
            proj_hl = "".join([f"<li>{html.escape(h)}</li>" for h in proj.highlights[:4]])
            proj_blocks.append(f"""
            <div class="project-entry">
                <div class="project-header">
                    <span class="project-name"><a href="{html.escape(proj.url or '')}">{html.escape(proj.name)}</a></span>
                    <span class="project-stack">{html.escape(proj.stack[:70])}</span>
                </div>
                <ul class="bullet-list">
                    {proj_hl}
                </ul>
            </div>
            """)

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(pi.full_name)} - {html.escape(meta['tailored_title'])} Resume</title>
    <style>
        @page {{
            size: A4;
            margin: 10mm 12mm 10mm 12mm;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #1a1a1a;
            line-height: 1.35;
            font-size: 9.8pt;
            background: #ffffff;
        }}
        a {{
            color: #0b57d0;
            text-decoration: none;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #0f172a;
            padding-bottom: 7px;
            margin-bottom: 8px;
        }}
        .candidate-name {{
            font-size: 20pt;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: #0f172a;
            text-transform: uppercase;
        }}
        .target-title {{
            font-size: 11pt;
            font-weight: 600;
            color: #0284c7;
            margin-top: 2px;
            margin-bottom: 4px;
        }}
        .contact-bar {{
            font-size: 8.8pt;
            color: #475569;
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .contact-bar span {{
            display: inline-block;
        }}
        .region-badge {{
            display: block;
            margin-top: 3px;
            font-size: 8.5pt;
            font-weight: 600;
            color: #047857;
        }}
        .section {{
            margin-top: 8px;
            margin-bottom: 4px;
        }}
        .section-title {{
            font-size: 10.5pt;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: #0f172a;
            border-bottom: 1px solid #cbd5e1;
            padding-bottom: 2px;
            margin-bottom: 5px;
        }}
        .summary-text {{
            font-size: 9.2pt;
            text-align: justify;
            color: #334155;
            line-height: 1.38;
        }}
        .skills-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9pt;
        }}
        .skills-table td {{
            padding: 2px 0;
            vertical-align: top;
        }}
        .skills-cat {{
            font-weight: 700;
            width: 22%;
            color: #1e293b;
        }}
        .skills-val {{
            color: #334155;
        }}
        .job-entry, .project-entry {{
            margin-bottom: 6px;
        }}
        .job-header, .project-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            font-size: 9.5pt;
            margin-bottom: 2px;
        }}
        .job-company, .project-name {{
            font-weight: 700;
            color: #0f172a;
        }}
        .job-role {{
            font-weight: 600;
            color: #0284c7;
        }}
        .job-duration, .project-stack {{
            font-size: 8.6pt;
            color: #64748b;
        }}
        .bullet-list {{
            margin-left: 16px;
            list-style-type: square;
        }}
        .bullet-list li {{
            font-size: 9pt;
            color: #334155;
            margin-bottom: 2px;
            line-height: 1.32;
        }}
        .edu-row {{
            display: flex;
            justify-content: space-between;
            font-size: 9.2pt;
        }}
        .edu-degree {{
            font-weight: 700;
            color: #0f172a;
        }}
        .edu-school {{
            color: #64748b;
        }}
        .edu-year {{
            font-weight: 600;
            color: #0f172a;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="candidate-name">{html.escape(pi.full_name)}</div>
        <div class="target-title">{html.escape(meta['tailored_title'])}</div>
        <div class="contact-bar">
            <span>📧 <a href="mailto:{html.escape(pi.email)}">{html.escape(pi.email)}</a></span>
            <span>📱 {html.escape(pi.phone)}</span>
            <span>🌐 <a href="{html.escape(pi.portfolio_url)}">Portfolio</a></span>
            <span>💻 <a href="{html.escape(pi.github_url)}">GitHub</a></span>
            <span>🔗 <a href="{html.escape(pi.linkedin_url)}">LinkedIn</a></span>
            <span>⚡ <a href="https://nnuikit.com/">NNUI-KIT (Author)</a></span>
        </div>
        <div class="region-badge">{html.escape(meta['region_badge'])}</div>
    </div>

    <div class="section">
        <div class="section-title">Professional Summary</div>
        <div class="summary-text">{html.escape(meta['summary'])}</div>
    </div>

    <div class="section">
        <div class="section-title">Technical Expertise</div>
        <table class="skills-table">
            <tr>
                <td class="skills-cat">Languages</td>
                <td class="skills-val">{html.escape(lang_str)}</td>
            </tr>
            <tr>
                <td class="skills-cat">Frameworks & Web</td>
                <td class="skills-val">{html.escape(fw_str)}</td>
            </tr>
            <tr>
                <td class="skills-cat">Architecture & Systems</td>
                <td class="skills-val">{html.escape(sys_str)}</td>
            </tr>
            <tr>
                <td class="skills-cat">Cloud & Databases</td>
                <td class="skills-val">{html.escape(db_str)}</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <div class="section-title">Professional Experience</div>
        {"".join(exp_blocks)}
    </div>

    <div class="section">
        <div class="section-title">Architectural Projects & Open Source</div>
        {"".join(proj_blocks)}
    </div>

    <div class="section">
        <div class="section-title">Education</div>
        <div class="edu-row">
            <div>
                <span class="edu-degree">{html.escape(self.profile.education.degree)}</span>
                <span class="edu-school"> — {html.escape(self.profile.education.institution)}</span>
            </div>
            <span class="edu-year">{html.escape(self.profile.education.graduation_year)}</span>
        </div>
    </div>
</body>
</html>
"""
        return html_template

    def build_resume_pdf(self, job_data: Dict[str, Any]) -> str:
        """
        Renders the tailored HTML resume to an ATS-compliant PDF using Playwright.
        Returns the absolute filepath to the created PDF.
        """
        from playwright.sync_api import sync_playwright

        job_id = job_data.get("id", "preview")
        company = re.sub(r'[^a-zA-Z0-9_-]', '_', job_data.get("company", "company")).strip("_")
        pdf_filename = f"Harsh_Parmar_{company}_{job_id[:8]}.pdf"
        html_filename = f"Harsh_Parmar_{company}_{job_id[:8]}.html"

        pdf_path = self.resumes_dir / pdf_filename
        html_path = self.resumes_dir / html_filename

        html_content = self.generate_html(job_data)
        html_path.write_text(html_content, encoding="utf-8")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_content, wait_until="networkidle")
            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                margin={
                    "top": "8mm",
                    "bottom": "8mm",
                    "left": "10mm",
                    "right": "10mm"
                }
            )
            browser.close()

        # Update in database if job has an ID
        if job_data.get("id"):
            update_job_resume(job_data["id"], str(pdf_path.resolve()))

        return str(pdf_path.resolve())
