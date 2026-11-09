# Career Compass

Career Compass is a career-support prototype based on the attached minor project report. It includes a Streamlit dashboard for professionals, a recruiter-facing resume matcher, a career toolkit, optional OpenAI career analysis, live remote listings from Remotive, optional LinkedIn/Naukri retrieval through Apify Actors, and an MCP server with `fetch_linkedin` and `fetch_naukri` tools.

## Features

- Extract selectable text from multi-page PDF resumes with PyMuPDF.
- Show a profile summary, detected skills, role-specific skill gaps, a learning roadmap, and search keywords. Analysis uses OpenAI when configured and a local analyzer otherwise.
- Retrieve actual remote vacancies from Remotive's public feed when Apify credentials are absent. Results are cached for six hours, ranked against the resume, and linked to the original Remotive listing.
- Retrieve jobs from configured Apify Actors concurrently and rank listings using explainable skill and text matching. If an Actor omits a direct listing URL, the app links to a role search on that source.
- Compare multiple candidate resumes against a job description for recruiter review.
- Filter jobs and candidates by match score, filter professional results by source and location, and download review CSVs.
- Save jobs to a local shortlist, track application status and notes, and export the application tracker.
- Expose job retrieval as MCP tools for compatible clients.
- Create role-specific interview practice questions and save answer notes for review.
- Draft clearer resume bullet variants from user-provided experience and verified outcomes, without inventing metrics.
- Generate and download a customizable 30-60-90 day role onboarding plan.

## Matching contribution

The matching method combines required skill coverage (55%), preferred skill coverage (10%), resume/job text overlap (20%), and target-role/title fit (15%). If a component cannot be calculated, the available weights are rescaled to sum to 100%. The app shows the component values, the resume line supporting each matched skill, and job-description lines for requirements not found in the resume text. “Not found” describes extracted evidence, not a claim that a person lacks a skill.

The professional workspace also has a one-skill what-if control. It recalculates the scores as if a selected missing skill were demonstrated, while keeping the original resume unchanged and marking the scenario as hypothetical. This gives the user a concrete view of how one skill could affect job ordering.

Job seekers can save listings to a local SQLite shortlist and track statuses from Saved through Applied, Interview, Offer, Rejected, or Withdrawn, with notes and CSV export. The employer workspace can filter candidates by match score and export a CSV containing score components and matched or missing job skills. The tracker stores listing fields and application notes only; it does not store uploaded resume text.

The [synthetic evaluation](evaluation/README.md) compares this scorer with the previous word-overlap ranker on the 20 employer samples. In the current curated set, nDCG@5 moves from 0.9165 to 1.0000; Precision@5 and MRR remain 1.0000 for both. This is a reproducible prototype result on hand-labeled synthetic data, not evidence of real-world hiring accuracy.

## Run locally

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

The app works without API credentials. The professional workspace retrieves real remote job posts from Remotive by default. Add `OPENAI_API_KEY` to `.env` to enable GPT analysis; without it, the local analyzer is used. OpenAI calls receive resume text, so only configure this if you are comfortable sending the uploaded text to that service.

## Live job retrieval

Without Apify credentials, the app uses Remotive's public API for live remote listings. Remotive requests attribution and a link to each original posting; the app displays both. Its public feed can be delayed by up to 24 hours and does not cover every location or on-site role. The resume search ranks cached feed results locally.

To use current LinkedIn and Naukri results instead of Remotive, create an Apify API token and paste it with the Actor IDs into the project-root `.env` file. The example IDs below use Actors whose inputs match this app (`searchQuery`, `location`, `maxItems`):

```dotenv
APIFY_API_TOKEN=paste-your-apify-token-here
APIFY_LINKEDIN_ACTOR_ID=jobscrawler~linkedin-job-scraper
APIFY_NAUKRI_ACTOR_ID=madeingermany~naukri-scraper
APIFY_MAX_JOBS=60
```

The app runs both configured Actors when you search. You can leave one Actor ID blank to use only the other; if no Apify token/Actor is configured, it uses Remotive. Actor runs may incur usage charges, so check each Actor's current Pricing tab. Apify's token is secret: do not paste it into `app.py`, commit `.env`, or share it in chat. Apify recommends keeping it private and using Bearer authentication; the app sends it that way.

## MCP server

Run the stdio MCP server with:

```bash
python mcp_server.py
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "career-compass": {
      "command": "/absolute/path/to/7th-sem-project/.venv/bin/python",
      "args": ["/absolute/path/to/7th-sem-project/mcp_server.py"],
      "env": {
        "APIFY_API_TOKEN": "your-token",
        "APIFY_LINKEDIN_ACTOR_ID": "owner~linkedin-jobs-actor",
        "APIFY_NAUKRI_ACTOR_ID": "owner~naukri-jobs-actor"
      }
    }
  }
}
```

The MCP tools use the same Apify environment variables as the dashboard. The report's production ambitions (robust scan-only PDF OCR, embeddings, guaranteed live-source coverage, and a sub-20-second retrieval SLA) require additional infrastructure and cannot be guaranteed by this prototype. The employer similarity score is advisory and should not be used as an automated hiring decision.

## Sample resumes

Forty fictional, selectable-text PDF resumes are included under `samples/`:

- `samples/professional_job_search/` contains 20 different profiles and target roles. Upload one PDF at a time in the professional workspace.
- `samples/employer_resume_match/` contains 20 candidates with varied overlap against `sample_job_description.txt`. Paste that description into the employer workspace, then upload the candidate PDFs together.

All sample identities and experience details are invented; the PDFs are labeled as synthetic. To regenerate them after editing the sample data, run `python scripts/generate_sample_resumes.py`.

## Project layout

```text
app.py                 Streamlit professional and employer workspaces
mcp_server.py          MCP stdio server and job tools
services/analysis.py   OpenAI and offline resume analysis
services/jobs.py       Remotive and Apify live retrieval and ranking
services/matching.py   Evidence-traceable scores and requirement extraction
services/resume.py     PDF extraction, skill detection, similarity scoring
services/tracker.py    Local shortlist and application tracker
```
