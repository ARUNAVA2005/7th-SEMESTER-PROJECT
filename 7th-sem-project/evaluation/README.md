# Synthetic matching evaluation

Run from the project root:

```bash
python scripts/evaluate_matching.py
```

The script compares the previous cosine word-overlap score with the proposed weighted matcher on the 20 fictional employer resumes and the included sample job description. `labels.csv` contains manually assigned relevance grades from 0 to 3 based on the written resume evidence: 3 = strong overlap with the role, 2 = meaningful but partial overlap, 1 = adjacent experience, and 0 = little relevant evidence. Relevance of 2 or more counts as relevant for Precision@5 and mean reciprocal rank.

The script reports nDCG@5, Precision@5, and MRR for both ranking methods, and writes per-candidate scores to `ranking_results.csv` plus aggregate metrics to `metrics.json`. These labels are a small, hand-curated synthetic benchmark, not expert hiring judgments or evidence of real-world validity. Results describe this one role and this fixed sample only.

Current run: the word-overlap baseline scores nDCG@5 = 0.9165, Precision@5 = 1.0000, and MRR = 1.0000. The explainable matcher scores nDCG@5 = 1.0000, Precision@5 = 1.0000, and MRR = 1.0000. On this set, the change affects ordering among relevant candidates; it does not improve whether the top five contain relevant candidates or how early the first relevant one appears. Re-run the script after any scoring or sample changes.
