"""Evidence-traceable matching shared by both user workflows."""

from __future__ import annotations

import re

from services.resume import SKILL_ALIASES, _skill_pattern, extract_skill_evidence, similarity_score

BASE_WEIGHTS = {
    "required_skill_coverage": 0.55,
    "preferred_skill_coverage": 0.10,
    "text_similarity": 0.20,
    "role_title_fit": 0.15,
}

PREFERRED_MARKERS = re.compile(r"\b(preferred|preferably|nice to have|bonus|optional|desirable|ideally)\b", re.I)
REQUIRED_SECTION = re.compile(r"\b(responsibilit(?:y|ies)|requirements?|qualifications?|must have|what you will do)\b", re.I)
PREFERRED_SECTION = re.compile(r"\b(preferred qualifications?|nice to have|bonus skills?|desirable skills?)\b", re.I)


def extract_job_requirements(job_text: str) -> dict[str, dict[str, str]]:
    """Find known skills in a job description and retain the line that supports each."""
    requirements: dict[str, dict[str, str]] = {}
    preferred_section = False
    lines = [line.strip(" •\t-*\r") for line in job_text.splitlines() if line.strip()]
    # Sentence splitting handles pasted job text that has no line breaks.
    if len(lines) <= 1:
        lines = [part.strip() for part in re.split(r"(?<=[.;])\s+", job_text) if part.strip()]
    for line in lines:
        if PREFERRED_SECTION.search(line):
            preferred_section = True
        elif REQUIRED_SECTION.search(line):
            preferred_section = False
        priority = "preferred" if preferred_section or PREFERRED_MARKERS.search(line) else "required"
        for skill, aliases in SKILL_ALIASES.items():
            if skill in requirements:
                # A later explicit preferred mention cannot demote a required one.
                if priority == "required":
                    requirements[skill]["priority"] = "required"
                continue
            if any(_skill_pattern(alias).search(line) for alias in aliases):
                requirements[skill] = {"priority": priority, "evidence": line[:220]}
    return requirements


def role_title_fit(job_title: str, target_role: str) -> float:
    """Cosine token fit between the user's target role and listing title."""
    if not job_title.strip() or not target_role.strip():
        return 0.0
    return similarity_score(target_role, job_title)


def score_match(
    profile_text: str,
    job_text: str,
    *,
    job_title: str = "",
    target_role: str = "",
    context_text: str = "",
    simulated_skills: tuple[str, ...] | list[str] = (),
) -> dict:
    """Score a profile/job pair and preserve text evidence for the explanation.

    A simulated skill affects skill coverage only. It never creates resume evidence
    and is intended solely for the what-if control in the professional workflow.
    """
    requirements = extract_job_requirements(job_text)
    profile_evidence = extract_skill_evidence(profile_text)
    available_skills = set(profile_evidence)
    for skill in simulated_skills:
        normalized = skill.casefold().strip()
        canonical = next((known for known, aliases in SKILL_ALIASES.items()
                          if normalized == known or normalized in aliases), normalized)
        available_skills.add(canonical)

    required = {skill: data for skill, data in requirements.items() if data["priority"] == "required"}
    preferred = {skill: data for skill, data in requirements.items() if data["priority"] == "preferred"}
    matched_required = sorted(set(required) & available_skills)
    missing_required = sorted(set(required) - available_skills)
    matched_preferred = sorted(set(preferred) & available_skills)
    missing_preferred = sorted(set(preferred) - available_skills)
    required_coverage = 100 * len(matched_required) / len(required) if required else None
    preferred_coverage = 100 * len(matched_preferred) / len(preferred) if preferred else None
    lexical_similarity = similarity_score(profile_text, f"{job_text}\n{context_text}".strip())
    title_fit = role_title_fit(job_title, target_role) if target_role and job_title else None

    components = {
        "required_skill_coverage": required_coverage,
        "preferred_skill_coverage": preferred_coverage,
        "text_similarity": lexical_similarity,
        "role_title_fit": title_fit,
    }
    active_weight = sum(BASE_WEIGHTS[key] for key, value in components.items() if value is not None)
    score = sum(BASE_WEIGHTS[key] * value for key, value in components.items() if value is not None) / active_weight

    evidence = {skill: profile_evidence[skill] for skill in matched_required + matched_preferred
                if skill in profile_evidence}
    requirement_evidence = {skill: requirements[skill]["evidence"] for skill in requirements}
    simulated = sorted(available_skills - set(profile_evidence))
    return {
        "match": round(score, 1),
        "components": {key: round(value, 1) if value is not None else None for key, value in components.items()},
        "required_skills": sorted(required),
        "preferred_skills": sorted(preferred),
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_preferred": matched_preferred,
        "missing_preferred": missing_preferred,
        "resume_evidence": evidence,
        "requirement_evidence": requirement_evidence,
        "simulated_skills": simulated,
    }
