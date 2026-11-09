"""Compare the legacy word-overlap ranker with the explainable skill matcher."""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.matching import score_match
from services.resume import similarity_score

SAMPLE_DIR = ROOT / "samples" / "employer_resume_match"
LABELS = ROOT / "evaluation" / "labels.csv"


def read_text(path: Path) -> str:
    with fitz.open(path) as document:
        return "\n".join(page.get_text("text", sort=True) for page in document)


def ndcg_at_k(rows: list[dict], score_key: str, k: int = 5) -> float:
    ranked = sorted(rows, key=lambda row: (-row[score_key], row["filename"]))[:k]
    ideal = sorted(rows, key=lambda row: (-row["relevance"], row["filename"]))[:k]

    def dcg(items: list[dict]) -> float:
        return sum((2 ** row["relevance"] - 1) / math.log2(position + 2)
                   for position, row in enumerate(items))

    best = dcg(ideal)
    return dcg(ranked) / best if best else 0.0


def precision_at_k(rows: list[dict], score_key: str, k: int = 5) -> float:
    ranked = sorted(rows, key=lambda row: (-row[score_key], row["filename"]))[:k]
    return sum(row["relevance"] >= 2 for row in ranked) / k


def reciprocal_rank(rows: list[dict], score_key: str) -> float:
    ranked = sorted(rows, key=lambda row: (-row[score_key], row["filename"]))
    for position, row in enumerate(ranked, 1):
        if row["relevance"] >= 2:
            return 1 / position
    return 0.0


def main() -> None:
    job_description = (SAMPLE_DIR / "sample_job_description.txt").read_text(encoding="utf-8")
    with LABELS.open(encoding="utf-8", newline="") as stream:
        labels = {row["filename"]: int(row["relevance"]) for row in csv.DictReader(stream)}
    rows = []
    for path in sorted(SAMPLE_DIR.glob("candidate_*.pdf")):
        profile = read_text(path)
        details = score_match(profile, job_description)
        rows.append({
            "filename": path.name,
            "relevance": labels[path.name],
            "baseline_score": similarity_score(profile, job_description),
            "proposed_score": details["match"],
            "required_coverage": details["components"]["required_skill_coverage"],
            "preferred_coverage": details["components"]["preferred_skill_coverage"],
        })

    metrics = {}
    for label, key in [("word_overlap_baseline", "baseline_score"), ("explainable_skill_matcher", "proposed_score")]:
        metrics[label] = {
            "nDCG@5": round(ndcg_at_k(rows, key), 4),
            "precision@5_relevance_2_or_higher": round(precision_at_k(rows, key), 4),
            "MRR_relevance_2_or_higher": round(reciprocal_rank(rows, key), 4),
        }

    output_csv = ROOT / "evaluation" / "ranking_results.csv"
    with output_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (-row["proposed_score"], row["filename"])))
    output_json = ROOT / "evaluation" / "metrics.json"
    output_json.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
