import os
import smtplib
import mimetypes
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from config.settings import CandidateProfile, load_profile
from agents.resume_builder import ResumeBuilder
from database.db import log_application_attempt, get_job_by_id, update_job_contact_email

load_dotenv()

class JobEmailer:
    """
    Automates tailored application & outreach emails via Gmail SMTP SSL.
    Generates personalized pitch letters referencing the target company's domain,
    role requirements, and country/regional fit, attaching the tailored ATS PDF resume.
    """

    def __init__(self, profile: Optional[CandidateProfile] = None):
        self.profile = profile or load_profile()
        self.resume_builder = ResumeBuilder(self.profile)
        
        self.gmail_user = os.getenv("GMAIL_USER", "harshparmar0421@gmail.com").strip()
        raw_pw = os.getenv("GMAIL_APP_PASSWORD", "").strip()
        # Clean spaces from app password if present
        self.gmail_password = raw_pw.replace(" ", "")

    def is_configured(self) -> bool:
        return bool(self.gmail_user and self.gmail_password)

    def generate_email_content(self, job_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Compose a highly tailored, non-generic application pitch based on the
        job description, company summary, funding background, and country.
        """
        analysis = self.resume_builder.analyze_role_and_region(job_data)
        pi = self.profile.personal_info
        role_type = analysis["role_type"]
        tailored_title = analysis["tailored_title"]
        company = job_data.get("company", "the Engineering Team")
        loc = (job_data.get("location") or "").lower()

        # Regional hook
        if any(k in loc for k in ["dubai", "uae", "emirates", "abu dhabi", "riyadh", "saudi", "middle east", "mena"]):
            loc_hook = (
                f"I am actively targeting roles in Dubai/UAE and the GCC region. "
                f"I am available for immediate relocation or rapid on-site onboarding with full visa readiness, having previously delivered enterprise data reporting platforms for clients in the region like NEOM."
            )
        elif any(k in loc for k in ["singapore", "sg", "apac"]):
            loc_hook = (
                f"I am aligned with APAC working hours and open to Singapore relocation. "
                f"I bring proven experience building high-throughput distributed platforms and developer-facing tooling."
            )
        elif any(k in loc for k in ["india", "bengaluru", "bangalore", "delhi", "mumbai", "hyderabad", "pune", "ahmedabad"]):
            loc_hook = (
                f"I am based in Ahmedabad, Gujarat, India, and available immediately / on 2 weeks notice for remote or hybrid engagement."
            )
        else:
            loc_hook = (
                f"Having worked with US-based remote engineering teams at AAVIL Inc (Delaware), I operate with high autonomy, disciplined asynchronous communication, and full overlap with US/EMEA working hours."
            )

        # Technical pitch hook
        if role_type == "frontend":
            tech_pitch = (
                f"As the creator and author of <strong>NNUI-KIT</strong> (<a href='https://nnuikit.com/'>nnuikit.com</a>), "
                f"I architected a 45-component platform-native Light-DOM UI library bundling under 38.9 kB gzipped (5x lighter than MUI/Mantine) "
                f"with native form participation via <code>ElementInternals</code> and multi-tab synchronization via <code>BroadcastChannel</code>. "
                f"At Oizom, I built the company-wide design system (30+ components) across SvelteKit, TypeScript, and Tailwind, reducing UI dev time by 50-80% and slashing initial page load times by 75% (<1s)."
            )
        elif role_type == "backend":
            tech_pitch = (
                f"At AAVIL Inc, I serve as SDE 2 and architect of the <strong>Decision Intelligence Platform</strong>, "
                f"a governed workflow engine. I engineered the server-authoritative DAG scheduling engine with topological sorting and dynamic variable interpolation, "
                f"scaled concurrent flow runner capacity from 20 to 80+ runners using PgBouncer connection pooling, "
                f"and isolated untrusted Python execution using WebAssembly (WASI CPython) with zero host disk/network access."
            )
        else:
            tech_pitch = (
                f"At AAVIL Inc, I serve as SDE 2 architecting the <strong>Decision Intelligence Platform</strong>, scaling distributed DAG execution to 80+ concurrent runners with PgBouncer connection pooling and WebAssembly (WASI) sandboxing. "
                f"In parallel, I am the creator of <strong>NNUI-KIT</strong> (<a href='https://nnuikit.com/'>nnuikit.com</a>), an open-source 45-component Light-DOM architecture bundling under 38.9 kB gzipped with native form serialization and cross-tab sync."
            )

        subject = f"Application: Harsh Parmar – {tailored_title} [{company}]"

        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        color: #1e293b;
        line-height: 1.6;
        font-size: 14px;
        background-color: #f8fafc;
        margin: 0;
        padding: 20px;
    }}
    .container {{
        max-width: 620px;
        margin: 0 auto;
        background: #ffffff;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        padding: 28px;
    }}
    h2 {{
        color: #0f172a;
        font-size: 18px;
        margin-top: 0;
        margin-bottom: 16px;
    }}
    p {{
        margin-bottom: 14px;
    }}
    .highlight-box {{
        background: #f1f5f9;
        border-left: 4px solid #0284c7;
        padding: 12px 16px;
        border-radius: 4px;
        margin: 16px 0;
        font-size: 13.5px;
    }}
    .links-bar {{
        margin-top: 20px;
        padding-top: 14px;
        border-top: 1px solid #e2e8f0;
        font-size: 13px;
        color: #64748b;
    }}
    a {{
        color: #0284c7;
        text-decoration: none;
        font-weight: 500;
    }}
    a:hover {{
        text-decoration: underline;
    }}
    .signature {{
        margin-top: 24px;
        color: #334155;
    }}
</style>
</head>
<body>
<div class="container">
    <h2>Hi {company} Hiring Team,</h2>
    
    <p>
        I am writing to express my strong interest in the <strong>{job_data.get('title', tailored_title)}</strong> role at <strong>{company}</strong>.
        {f"I've been following {company}'s impressive growth and work in {job_data.get('company_summary', '')}." if job_data.get('company_summary') else ''}
    </p>

    <div class="highlight-box">
        {tech_pitch}
    </div>

    <p>{loc_hook}</p>

    <p>
        I have attached my tailored resume for your review. You can also explore my live work, code repositories, and architectural projects below:
    </p>

    <div class="links-bar">
        ⚡ <strong>NNUI-KIT:</strong> <a href="https://nnuikit.com/">nnuikit.com</a><br>
        🌐 <strong>Portfolio:</strong> <a href="{pi.portfolio_url}">{pi.portfolio_url}</a><br>
        💻 <strong>GitHub:</strong> <a href="{pi.github_url}">{pi.github_url}</a><br>
        🔗 <strong>LinkedIn:</strong> <a href="{pi.linkedin_url}">{pi.linkedin_url}</a>
    </div>

    <div class="signature">
        <p>
            Looking forward to discussing how my experience can accelerate the engineering team at {company}.<br><br>
            Warm regards,<br>
            <strong>{pi.full_name}</strong><br>
            {tailored_title}<br>
            📞 {pi.phone} | ✉️ {pi.email}
        </p>
    </div>
</div>
</body>
</html>
"""

        # Clean text version for non-HTML email clients
        text_body = f"""Hi {company} Hiring Team,

I am writing to express my strong interest in the {job_data.get('title', tailored_title)} position at {company}.

Summary of relevant technical achievements:
- {role_type.upper()} FOCUS:
  {tech_pitch.replace('<br>', '\n').replace('<strong>', '').replace('</strong>', '').replace('<code>', '').replace('</code>', '')}

Location & Availability:
{loc_hook}

I have attached my tailored PDF resume for your review.
- NNUI-KIT Architecture: https://nnuikit.com/
- Portfolio: {pi.portfolio_url}
- GitHub: {pi.github_url}
- LinkedIn: {pi.linkedin_url}

Looking forward to hearing from you.

Warm regards,
{pi.full_name}
{tailored_title}
Phone: {pi.phone} | Email: {pi.email}
"""

        return {
            "subject": subject,
            "html": html_body,
            "text": text_body
        }

    def send_application_email(
        self,
        job_data: Dict[str, Any],
        to_email: Optional[str] = None,
        preview_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Builds tailored PDF resume, generates pitch email, and dispatches via Gmail SMTP SSL.
        
        If preview_mode=True (default), sends the email to harshparmar0421@gmail.com with
        a [TEST PREVIEW] tag, allowing real verification in Gmail inbox before any live submission.
        """
        if not self.is_configured():
            return {
                "success": False,
                "status": "FAILED",
                "error": "Gmail credentials (GMAIL_USER / GMAIL_APP_PASSWORD) not configured."
            }

        # 1. Generate or retrieve tailored resume PDF
        pdf_path = job_data.get("tailored_resume_path")
        if not pdf_path or not Path(pdf_path).exists():
            pdf_path = self.resume_builder.build_resume_pdf(job_data)

        # 2. Generate email pitch
        content = self.generate_email_content(job_data)
        company = job_data.get("company", "Company")

        # Determine recipient
        target_recipient = to_email or job_data.get("contact_email")
        if preview_mode or not target_recipient:
            recipient = self.gmail_user
            subject = f"[PREVIEW FOR {company.upper()}] {content['subject']}"
        else:
            recipient = target_recipient
            subject = content["subject"]

        # 3. Build MIME Message
        msg = MIMEMultipart("mixed")
        msg["From"] = f"{self.profile.personal_info.full_name} <{self.gmail_user}>"
        msg["To"] = recipient
        msg["Subject"] = subject
        if not preview_mode and target_recipient:
            # BCC yourself on live applications so you have a copy in sent/inbox
            msg["Bcc"] = self.gmail_user

        # Create alternative part for HTML + Text
        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(content["text"], "plain", "utf-8"))
        alt_part.attach(MIMEText(content["html"], "html", "utf-8"))
        msg.attach(alt_part)

        # 4. Attach Tailored PDF Resume
        pdf_file = Path(pdf_path)
        if pdf_file.exists():
            with open(pdf_file, "rb") as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                pdf_attachment.add_header(
                    "Content-Disposition", 
                    "attachment", 
                    filename=pdf_file.name
                )
                msg.attach(pdf_attachment)

        # 5. Dispatch via SMTP SSL
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                server.login(self.gmail_user, self.gmail_password)
                recipients = [recipient]
                if not preview_mode and target_recipient and self.gmail_user != target_recipient:
                    recipients.append(self.gmail_user)
                server.send_message(msg, from_addr=self.gmail_user, to_addrs=recipients)

            status = "EMAIL_PREVIEW_SENT" if preview_mode else "EMAIL_SENT"
            
            # Log in database
            if job_data.get("id"):
                log_application_attempt(
                    job_id=job_data["id"],
                    status=status,
                    submission_method="GMAIL_SMTP_SSL",
                    screenshot_path=pdf_path,
                    response_payload=f"Sent to {recipient} with subject '{subject}'"
                )

            return {
                "success": True,
                "status": status,
                "recipient": recipient,
                "subject": subject,
                "pdf_path": pdf_path,
                "preview_mode": preview_mode
            }

        except Exception as e:
            return {
                "success": False,
                "status": "FAILED",
                "error": str(e)
            }
