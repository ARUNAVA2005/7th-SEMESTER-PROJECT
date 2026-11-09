"""AI-assisted career analysis with a deterministic offline fallback."""

from __future__ import annotations

import json
import os

from services.resume import extract_skills, keywords


def _offline_analysis(resume_text: str, target_role: str) -> dict:
    skills = extract_skills(resume_text)
    terms = keywords(resume_text)
    role_skills = {
        "software engineer": ["python", "java", "git", "sql", "rest api", "docker"],
        "full stack developer": ["javascript", "typescript", "react", "node.js", "sql", "rest api", "git"],
        "data scientist": ["python", "sql", "machine learning", "pytorch", "data analysis", "statistics"],
        "data analyst": ["sql", "excel", "data analysis", "power bi", "tableau", "python"],
        "frontend developer": ["javascript", "typescript", "react", "html", "css", "git"],
        "backend developer": ["python", "java", "sql", "postgresql", "rest api", "docker"],
        "product manager": ["agile", "communication", "leadership", "data analysis", "excel"],
    }
    normalized_role = target_role.strip().lower()
    expected = next((v for k, v in role_skills.items() if k in normalized_role or normalized_role in k),
                    ["communication", "sql", "python", "git"])
    gaps = [skill for skill in expected if skill not in skills]
    summary = (f"Your resume highlights {', '.join(skills[:5]) or 'a developing professional profile'}. "
               f"For a {target_role or 'target'} role, emphasize measurable outcomes, project scope, "
               "and how your work improved a product or process.")
    return {
        "summary": summary,
        "skills": skills,
        "gaps": gaps,
        "roadmap": [
            f"Strengthen {gaps[0] if gaps else 'one advanced skill'} with a focused course and a small portfolio project.",
            "Build one role-relevant project that demonstrates end-to-end problem solving.",
            "Rewrite experience bullets with clear action, scope, and measurable impact.",
        ],
        "keywords": terms,
        "provider": "Built-in analyzer",
    }


def analyze_resume(resume_text: str, target_role: str) -> dict:
    """Return structured career insights, using OpenAI only when configured."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return _offline_analysis(resume_text, target_role)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": (
                    "You are a careful career coach. Analyze only evidence in the resume; distinguish "
                    "inference from fact. Return JSON with summary (string), skills (string array), "
                    "gaps (string array), roadmap (3-5 actionable strings), keywords (string array). "
                    "Do not invent credentials or claim a candidate is objectively qualified."
                )},
                {"role": "user", "content": f"Target role: {target_role}\nResume text:\n{resume_text[:18000]}"},
            ],
            temperature=0.2,
        )
        result = json.loads(response.choices[0].message.content or "{}")
        result.setdefault("skills", extract_skills(resume_text))
        result.setdefault("keywords", keywords(resume_text))
        result.setdefault("gaps", [])
        result.setdefault("roadmap", [])
        result.setdefault("summary", "Analysis completed.")
        result["provider"] = "OpenAI"
        return result
    except Exception as exc:
        result = _offline_analysis(resume_text, target_role)
        result["provider"] = f"Built-in analyzer (AI unavailable: {exc.__class__.__name__})"
        return result
