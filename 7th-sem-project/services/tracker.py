"""Local SQLite storage for a job seeker's shortlist and application progress."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "career_compass.sqlite3"
APPLICATION_STATUSES = ("Saved", "Applied", "Interview", "Offer", "Rejected", "Withdrawn")


def job_key(job: dict) -> str:
    """Build a stable local identifier from public listing fields."""
    parts = [job.get(field, "") for field in ("source", "title", "company", "location", "url")]
    return hashlib.sha256("|".join(str(part).strip().casefold() for part in parts).encode("utf-8")).hexdigest()[:20]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS saved_jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT NOT NULL,
            match_score REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Saved',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    return connection


def list_saved_jobs() -> list[dict]:
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM saved_jobs ORDER BY updated_at DESC, title").fetchall()
    return [dict(row) for row in rows]


def save_job(job: dict) -> str:
    identifier = job_key(job)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as connection:
        connection.execute("""
            INSERT INTO saved_jobs (job_id, title, company, location, source, url, match_score,
                                    status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Saved', '', ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                title=excluded.title, company=excluded.company, location=excluded.location,
                source=excluded.source, url=excluded.url, match_score=excluded.match_score,
                updated_at=excluded.updated_at
        """, (identifier, job.get("title", "Role"), job.get("company", "Company"),
              job.get("location", ""), job.get("source", ""), job.get("url", ""),
              float(job.get("match", 0)), now, now))
    return identifier


def update_job(job_id: str, status: str, notes: str) -> None:
    if status not in APPLICATION_STATUSES:
        raise ValueError("Unknown application status")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as connection:
        connection.execute("UPDATE saved_jobs SET status=?, notes=?, updated_at=? WHERE job_id=?",
                           (status, notes[:4000], now, job_id))


def remove_job(job_id: str) -> None:
    with _connect() as connection:
        connection.execute("DELETE FROM saved_jobs WHERE job_id=?", (job_id,))
