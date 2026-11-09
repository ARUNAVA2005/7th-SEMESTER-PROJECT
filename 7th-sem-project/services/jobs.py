"""Live job retrieval from configured Apify Actors or Remotive's public feed."""

from __future__ import annotations

import os
import re
import html
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus, urlparse

import requests
import streamlit as st

from services.matching import score_match

def _search_url(source: str, title: str, location: str) -> str:
    """Build a search-results URL when a listing has no direct URL."""
    query = quote_plus(title.strip() or "jobs")
    place = quote_plus(location.strip() or "India")
    if source.casefold() == "naukri":
        # Naukri's keyword/location route opens matching search results.
        slug = "-".join((title.strip() or "jobs").lower().split())
        place_slug = "-".join((location.strip() or "india").lower().split())
        return f"https://www.naukri.com/{slug}-jobs-in-{place_slug}"
    return f"https://www.linkedin.com/jobs/search/?keywords={query}&location={place}"


@st.cache_data(ttl=6 * 60 * 60, max_entries=1, show_spinner=False)
def _fetch_remotive_catalog() -> list[dict]:
    """Cache the public remote-job feed to respect its low request limits."""
    response = requests.get(
        "https://remotive.com/api/remote-jobs",
        params={"limit": 1000},
        headers={"User-Agent": "CareerCompass/1.0 (job discovery app)"},
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()
    jobs = []
    for row in payload.get("jobs", []):
        raw_description = row.get("description") or ""
        description = html.unescape(re.sub(r"<[^>]+>", " ", raw_description))
        description = " ".join(description.split())
        jobs.append({
            "title": row.get("title") or "Untitled role",
            "company": row.get("company_name") or "Company not listed",
            "location": row.get("candidate_required_location") or "Remote; check employer eligibility",
            "description": description,
            "url": row.get("url") or "https://remotive.com/remote-jobs",
            "source": "Remotive",
            "salary": row.get("salary") or "",
            "publication_date": row.get("publication_date") or "",
            "job_type": row.get("job_type") or "",
            "tags": row.get("tags") or [],
        })
    return jobs


def _role_matches(job: dict, query: str) -> bool:
    """Keep feed search relevant while searching locally against the cached catalog."""
    terms = [term.lower() for term in re.findall(r"[a-zA-Z0-9+#.]+", query)
             if term.lower() not in {"and", "or", "the", "for", "with", "to", "in"}]
    if not terms:
        return True
    title = job.get("title", "").casefold()
    searchable = " ".join([
        title, job.get("company", ""), job.get("description", ""),
        " ".join(job.get("tags", [])), job.get("job_type", ""),
    ]).casefold()
    return any(term in searchable for term in terms) or all(term in title for term in terms)


def _fetch_actor(actor_id: str, source: str, query: str, location: str, limit: int) -> list[dict]:
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not token or not actor_id:
        return []
    response = requests.post(
        f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items",
        params={"format": "json", "clean": "true", "limit": limit},
        headers={"Authorization": f"Bearer {token}"},
        json={"searchQuery": query, "location": location, "maxItems": limit}, timeout=35,
    )
    response.raise_for_status()
    jobs = []
    for row in response.json():
        title = row.get("title") or row.get("positionName") or row.get("jobTitle") or "Untitled role"
        row_location = row.get("location") or row.get("locationName") or row.get("locations") or location
        if isinstance(row_location, dict):
            row_location = row_location.get("raw") or ", ".join(str(value) for value in row_location.values() if value)
        elif isinstance(row_location, (list, tuple)):
            row_location = ", ".join(str(value) for value in row_location if value)
        raw_company = row.get("company") or row.get("companyName") or row.get("company_name") or "Company not listed"
        if isinstance(raw_company, dict):
            raw_company = raw_company.get("name") or raw_company.get("companyName") or "Company not listed"
        direct_url = (row.get("url") or row.get("jobUrl") or row.get("job_url")
                      or row.get("staticUrl") or row.get("applyRedirectUrl") or row.get("link") or "")
        if not direct_url or urlparse(direct_url).path in ("", "/"):
            direct_url = _search_url(source, title, row_location)
        jobs.append({
            "title": title,
            "company": raw_company,
            "location": row_location,
            "description": row.get("description") or row.get("descriptionText") or row.get("jobDescription") or "",
            "url": direct_url,
            "source": source,
            "salary": row.get("salary") or row.get("salaryText") or "",
            "publication_date": row.get("publication_date") or row.get("postedAt") or row.get("postedDate") or row.get("postedAtIso") or "",
        })
    return jobs


def fetch_jobs(query: str, location: str = "India", limit: int = 60) -> tuple[list[dict], bool]:
    """Fetch live listings from configured Apify actors or the public Remotive feed."""
    actors = [(os.getenv("APIFY_LINKEDIN_ACTOR_ID", ""), "LinkedIn"),
              (os.getenv("APIFY_NAUKRI_ACTOR_ID", ""), "Naukri")]
    configured = [(actor, source) for actor, source in actors if actor]
    if not os.getenv("APIFY_API_TOKEN", "").strip() or not configured:
        try:
            catalog = _fetch_remotive_catalog()
        except Exception as exc:
            raise RuntimeError("Could not load live listings from Remotive. Check your internet connection and try again.") from exc
        matches = [job for job in catalog if _role_matches(job, query)]
        return matches[:limit], False
    results: list[dict] = []
    errors = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_fetch_actor, actor, source, query, location, limit // len(configured))
                   for actor, source in configured]
        for future in futures:
            try:
                results.extend(future.result())
            except Exception as exc:
                errors.append(exc)
    if not results and errors:
        raise RuntimeError("Apify job retrieval failed. Check your token, Actor IDs, and Actor input format.") from errors[0]
    return results, False


def rank_jobs(
    jobs: list[dict],
    profile: str,
    query: str = "",
    simulated_skills: tuple[str, ...] | list[str] = (),
) -> list[dict]:
    """Rank listings with explainable requirement, text, and title components."""
    for job in jobs:
        job_text = job.get("description", "")
        details = score_match(
            profile,
            job_text,
            job_title=job.get("title", ""),
            target_role=query,
            context_text=job.get("title", ""),
            simulated_skills=simulated_skills,
        )
        job["match"] = details["match"]
        job["match_details"] = details
    return sorted(jobs, key=lambda item: item["match"], reverse=True)
