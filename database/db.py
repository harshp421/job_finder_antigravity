import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from database.models import SCHEMA_SQL

DB_PATH = Path(__file__).parent.parent / "data" / "job_pipeline.db"

def get_connection() -> sqlite3.Connection:
    """Get SQLite database connection, ensuring data directory exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database schema and run migrations."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        # Migrations for existing database
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "company_summary" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN company_summary TEXT")
        if "funding_info" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN funding_info TEXT")
        if "tailored_resume_path" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN tailored_resume_path TEXT")
        if "contact_email" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN contact_email TEXT")
        conn.commit()

def get_job_by_id(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single job posting by exact ID or prefix match."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            # Try prefix match if user entered short ID
            cursor.execute("SELECT * FROM jobs WHERE id LIKE ? LIMIT 1", (f"{job_id}%",))
            row = cursor.fetchone()
        return dict(row) if row else None

def update_job_resume(job_id: str, resume_path: str):
    """Save the path to a tailored resume for a specific job."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET tailored_resume_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (resume_path, job_id)
        )
        conn.commit()

def update_job_contact_email(job_id: str, email: str):
    """Save recruiter or contact email for a job."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET contact_email = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (email, job_id)
        )
        conn.commit()

def generate_job_id(company: str, title: str, job_url: str) -> str:
    """Create a deterministic unique ID based on company, title, and URL."""
    raw = f"{company.lower().strip()}_{title.lower().strip()}_{job_url.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

def save_job(job_data: Dict[str, Any]) -> bool:
    """
    Insert a job posting into the database.
    Returns True if newly inserted, False if already exists.
    """
    job_id = job_data.get("id") or generate_job_id(
        job_data["company"], job_data["title"], job_data["job_url"]
    )
    
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO jobs (
                    id, title, company, location, is_remote, job_url, 
                    source, ats_type, salary_raw, min_salary, max_salary, 
                    description, company_summary, funding_info, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_url) DO UPDATE SET
                    company_summary = COALESCE(excluded.company_summary, jobs.company_summary),
                    funding_info = COALESCE(excluded.funding_info, jobs.funding_info)
                """,
                (
                    job_id,
                    job_data.get("title", ""),
                    job_data.get("company", ""),
                    job_data.get("location", ""),
                    1 if job_data.get("is_remote", True) else 0,
                    job_data.get("job_url", ""),
                    job_data.get("source", "unknown"),
                    job_data.get("ats_type", ""),
                    job_data.get("salary_raw", ""),
                    job_data.get("min_salary"),
                    job_data.get("max_salary"),
                    job_data.get("description", ""),
                    job_data.get("company_summary"),
                    job_data.get("funding_info"),
                    job_data.get("status", "DISCOVERED")
                )
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error saving job: {e}")
            return False

def get_unscored_jobs(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch jobs that need AI match scoring."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM jobs 
            WHERE match_score IS NULL AND status = 'DISCOVERED'
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

def update_job_score(job_id: str, score: int, rationale: str, status: str):
    """Update job evaluation score and status."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE jobs 
            SET match_score = ?, match_rationale = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (score, rationale, status, job_id)
        )
        conn.commit()

def get_jobs_ready_for_application(min_score: int = 75, limit: int = 25) -> List[Dict[str, Any]]:
    """Retrieve top matched jobs queued for application."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM jobs 
            WHERE match_score >= ? AND status = 'QUEUED'
            ORDER BY match_score DESC, created_at DESC 
            LIMIT ?
            """,
            (min_score, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

def log_application_attempt(
    job_id: str, 
    status: str, 
    submission_method: str, 
    screenshot_path: Optional[str] = None, 
    error_message: Optional[str] = None,
    response_payload: Optional[str] = None
):
    """Log an application submission attempt."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO applications (
                job_id, status, submission_method, screenshot_path, error_message, response_payload
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (job_id, status, submission_method, screenshot_path, error_message, response_payload)
        )
        # Update job status
        new_job_status = "APPLIED" if status == "SUBMITTED" else "FAILED"
        cursor.execute(
            "UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_job_status, job_id)
        )
        conn.commit()

def get_statistics() -> Dict[str, Any]:
    """Retrieve comprehensive pipeline counters and breakdowns."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_discovered = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE match_score IS NOT NULL")
        total_evaluated = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'QUEUED'")
        total_queued = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'APPLIED'")
        total_applied = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'SKIPPED'")
        total_skipped = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(match_score) FROM jobs WHERE match_score IS NOT NULL")
        avg_score = cursor.fetchone()[0] or 0.0

        # Breakdown by Source
        cursor.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source")
        source_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Breakdown by Company
        cursor.execute("SELECT company, COUNT(*) FROM jobs GROUP BY company ORDER BY COUNT(*) DESC LIMIT 8")
        company_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Application statuses
        cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
        app_statuses = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_discovered": total_discovered,
            "total_evaluated": total_evaluated,
            "total_queued": total_queued,
            "total_applied": total_applied,
            "total_skipped": total_skipped,
            "average_match_score": round(avg_score, 1),
            "sources": source_counts,
            "companies": company_counts,
            "application_statuses": app_statuses
        }
