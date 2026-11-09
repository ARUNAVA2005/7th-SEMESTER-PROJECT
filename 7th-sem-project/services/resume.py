"""Resume extraction, lightweight NLP, and relevance scoring."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

SKILL_ALIASES = {
    "python": ("python",), "java": ("java",), "javascript": ("javascript", "java script"),
    "typescript": ("typescript", "type script"), "react": ("react", "react.js", "reactjs"),
    "node.js": ("node.js", "nodejs", "node js"), "express": ("express", "express.js", "expressjs"),
    "fastapi": ("fastapi", "fast api"), "flask": ("flask",), "django": ("django",),
    "sql": ("sql",), "postgresql": ("postgresql", "postgres", "postgre sql"),
    "mongodb": ("mongodb", "mongo db"), "mysql": ("mysql", "my sql"),
    "aws": ("aws", "amazon web services"), "azure": ("azure",), "gcp": ("gcp", "google cloud platform"),
    "docker": ("docker",), "kubernetes": ("kubernetes", "k8s"), "git": ("git",),
    "machine learning": ("machine learning", "ml"), "deep learning": ("deep learning",),
    "natural language processing": ("natural language processing", "nlp"),
    "large language models": ("large language models", "large language model", "llm", "llms"),
    "pytorch": ("pytorch", "py torch"), "tensorflow": ("tensorflow", "tensor flow"),
    "scikit-learn": ("scikit-learn", "scikit learn", "sklearn"),
    "data analysis": ("data analysis", "data analytics"),
    "power bi": ("power bi", "powerbi"), "tableau": ("tableau",), "excel": ("excel",),
    "html": ("html", "html5"), "css": ("css", "css3"),
    "rest api": ("rest api", "rest apis", "restful api", "restful apis"),
    "graphql": ("graphql", "graph ql"), "agile": ("agile",),
    "communication": ("communication",), "leadership": ("leadership",),
    "testing": ("testing", "unit tests", "integration tests", "test automation"),
    "accessibility": ("accessibility",), "figma": ("figma",), "selenium": ("selenium",),
    "linux": ("linux",), "redis": ("redis",), "terraform": ("terraform",),
}

SKILLS = list(SKILL_ALIASES)

STOP_WORDS = set("""a an and are as at be by for from has have in into is it its of on or
that the their this to with will your you our we experience work looking role candidate
years responsible ability strong team skills required preferred including using across""".split())


def extract_pdf_text(filename: str, content: bytes) -> str:
    """Extract and normalize text from a PDF, rejecting image-only documents."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - environment setup issue
        raise RuntimeError("PyMuPDF is required. Install dependencies with pip install -r requirements.txt.") from exc
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            text = "\n".join(page.get_text("text", sort=True) for page in document)
    except Exception as exc:
        raise ValueError(f"Could not read {Path(filename).name}: {exc}") from exc
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 40:
        raise ValueError("This PDF has too little selectable text. Please upload a text-based PDF.")
    return text


def _skill_pattern(alias: str) -> re.Pattern[str]:
    words = re.escape(alias).replace(r"\ ", r"\s+")
    return re.compile(r"(?<![\w])" + words + r"(?![\w])", re.IGNORECASE)


def extract_skill_evidence(text: str) -> dict[str, str]:
    """Map each recognized skill to the first source line that contains it."""
    evidence: dict[str, str] = {}
    lines = [line.strip(" •\t-*\r") for line in text.splitlines() if line.strip()]
    for line in lines:
        for canonical, aliases in SKILL_ALIASES.items():
            if canonical in evidence:
                continue
            if any(_skill_pattern(alias).search(line) for alias in aliases):
                evidence[canonical] = line[:220]
    return evidence


def extract_skills(text: str) -> list[str]:
    return list(extract_skill_evidence(text))


def keywords(text: str, limit: int = 12) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z+#.\-]{1,}", text.lower())
    counts = Counter(w for w in words if w not in STOP_WORDS and len(w) > 2)
    ranked = [word for word, _ in counts.most_common(limit * 2)]
    known = extract_skills(text)
    return list(dict.fromkeys(known + ranked))[:limit]


def similarity_score(left: str, right: str) -> float:
    """Cosine similarity over normalized word counts, returned as 0..100."""
    def vector(text: str) -> Counter[str]:
        return Counter(w for w in re.findall(r"[a-zA-Z][a-zA-Z+#.\-]{1,}", text.lower()) if w not in STOP_WORDS)
    a, b = vector(left), vector(right)
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(word, 0) for word, value in a.items())
    denom = (sum(x * x for x in a.values()) ** 0.5) * (sum(x * x for x in b.values()) ** 0.5)
    return round(100 * dot / denom, 1) if denom else 0.0
