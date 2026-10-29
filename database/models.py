from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field
import sqlite3
import json

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    is_remote INTEGER DEFAULT 1,
    job_url TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    ats_type TEXT, -- greenhouse, lever, workday, direct, etc.
    salary_raw TEXT,
    min_salary REAL,
    max_salary REAL,
    description TEXT,
    company_summary TEXT DEFAULT NULL,
    funding_info TEXT DEFAULT NULL,
    match_score INTEGER DEFAULT NULL,
    match_rationale TEXT DEFAULT NULL,
    status TEXT DEFAULT 'DISCOVERED', -- DISCOVERED, EVALUATED, QUEUED, APPLIED, SKIPPED, FAILED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    status TEXT NOT NULL, -- PENDING, SUBMITTED, FAILED
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submission_method TEXT, -- ATS_API, BROWSER_AUTOMATION, MANUAL
    screenshot_path TEXT,
    error_message TEXT,
    response_payload TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs (id)
);

CREATE TABLE IF NOT EXISTS answer_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_hash TEXT UNIQUE NOT NULL,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs (match_score);
"""
