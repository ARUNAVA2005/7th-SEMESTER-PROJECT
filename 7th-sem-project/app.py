"""Career Compass: resume insights, job discovery, employer matching, and career tools."""

from __future__ import annotations

import csv
import io
import os

import streamlit as st
from dotenv import load_dotenv

from services.analysis import analyze_resume
from services.jobs import fetch_jobs, rank_jobs
from services.matching import score_match
from services.resume import extract_pdf_text, extract_skills
from services.tracker import (
    APPLICATION_STATUSES,
    job_key,
    list_saved_jobs,
    remove_job,
    save_job,
    update_job,
)

load_dotenv()
st.set_page_config(page_title="Career Compass", page_icon=":material/explore:", layout="wide")


def csv_download(rows: list[dict], columns: list[str]) -> bytes:
    """Serialize selected fields safely for spreadsheet programs."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        safe_row = {}
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, (list, tuple, set)):
                value = "; ".join(str(part) for part in value)
            value = str(value)
            if value.lstrip().startswith(("=", "+", "-", "@")):
                value = "'" + value
            safe_row[column] = value
        writer.writerow(safe_row)
    return buffer.getvalue().encode("utf-8-sig")


def render_match_explanation(details: dict) -> None:
    """Show score components, matched skills, gaps, and supporting text."""
    components = details["components"]
    values = [("Required skills", components["required_skill_coverage"]),
              ("Preferred skills", components["preferred_skill_coverage"]),
              ("Text overlap", components["text_similarity"]),
              ("Role title", components["role_title_fit"])]
    present = [(label, value) for label, value in values if value is not None]
    cols = st.columns(len(present))
    for col, (label, value) in zip(cols, present):
        col.metric(label, f"{value:.0f}%")

    if details["matched_required"]:
        st.markdown("**Required skills found in resume**: " + ", ".join(details["matched_required"]))
    if details["missing_required"]:
        st.markdown("**Required skills not found in resume text**: " + ", ".join(details["missing_required"]))
    if details["matched_preferred"]:
        st.markdown("**Preferred skills found in resume**: " + ", ".join(details["matched_preferred"]))
    if details["missing_preferred"]:
        st.markdown("**Preferred skills not found in resume text**: " + ", ".join(details["missing_preferred"]))
    if not details["required_skills"] and not details["preferred_skills"]:
        st.caption("No skills from the built-in taxonomy were identified in this description; the score relies on text overlap.")
    with st.expander("Evidence behind this score"):
        for skill, snippet in details["resume_evidence"].items():
            st.markdown(f"- **{skill}** in resume: “{snippet}”")
        for skill in details["missing_required"] + details["missing_preferred"]:
            st.markdown(f"- **{skill}** requirement: “{details['requirement_evidence'][skill]}”")


def render_career_toolkit() -> None:
    """Render interview practice, resume bullet coaching, and onboarding planning."""
    st.subheader("Career toolkit")
    st.write("Practice interviews, improve resume bullets, and build a role-specific first-90-days plan.")
    interview_tab, bullet_tab, plan_tab = st.tabs(["Interview studio", "Resume bullet coach", "30-60-90 day plan"])

    with interview_tab:
        st.markdown("#### Build a practice set")
        role = st.text_input("Target role", key="toolkit_interview_role", placeholder="e.g. Data analyst")
        jd = st.text_area("Paste a job description (optional)", key="toolkit_interview_jd", height=130)
        focus = st.multiselect("Question focus", ["Behavioral", "Technical", "Situational"], default=["Behavioral", "Technical"], key="toolkit_interview_focus")
        skills = extract_skills(jd) if jd.strip() else []
        if st.button("Create interview practice set", type="primary", key="create_interview_set"):
            if not role.strip():
                st.error("Enter a target role to create relevant practice questions.")
            else:
                questions = []
                if "Behavioral" in focus:
                    questions.extend([
                        f"Tell me about a project or result that shows you are ready for a {role.strip()} role.",
                        "Describe a time you received difficult feedback. What changed in your approach?",
                        "Tell me about a disagreement on a team and how you helped resolve it.",
                    ])
                if "Technical" in focus:
                    questions.extend([f"Walk me through how you used {skill} in a real project and how you measured the result." for skill in skills[:5]])
                    questions.append(f"What technical problem would you expect to solve first as a {role.strip()}, and how would you approach it?")
                if "Situational" in focus:
                    questions.extend([
                        "A key deliverable is at risk and a teammate is blocked. What would you do first?",
                        "You have two urgent requests from different stakeholders. How would you prioritize and communicate?",
                    ])
                if not questions:
                    questions = [f"Why are you interested in working as a {role.strip()}?", "Describe a project where you solved a difficult problem."]
                st.session_state["toolkit_questions"] = questions
                st.session_state["toolkit_answers"] = {}
        questions = st.session_state.get("toolkit_questions", [])
        if questions:
            st.markdown("#### Practice and review your answers")
            question = st.selectbox("Practice question", questions, key="toolkit_active_question")
            answer = st.text_area("Your answer", key=f"answer_{questions.index(question)}", height=150, placeholder="Use STAR: Situation, Task, Action, Result. Keep examples accurate and specific.")
            st.caption("Self-review: did you explain your personal actions, the outcome, and what you learned?")
            if st.button("Save practice answer", key="save_practice_answer"):
                st.session_state.setdefault("toolkit_answers", {})[question] = answer
                st.success("Answer saved in this session.")
            if st.session_state.get("toolkit_answers"):
                notes = "\n\n".join(f"Q: {q}\nA: {a}" for q, a in st.session_state["toolkit_answers"].items())
                st.download_button("Download interview practice notes", notes, file_name="interview_practice_notes.txt", mime="text/plain")

    with bullet_tab:
        st.markdown("#### Make experience easier to scan")
        draft = st.text_area("Current resume bullet", height=110, placeholder="Describe what you did, the tools or methods used, and the outcome.")
        result = st.text_input("Verified result or scale (optional)", placeholder="e.g. reduced processing time by 20% across 4 reports")
        role_context = st.text_input("Target role or skill to emphasize (optional)", placeholder="e.g. Python automation")
        if st.button("Draft stronger versions", type="primary", key="rewrite_bullet"):
            if len(draft.strip()) < 12:
                st.error("Add a complete draft bullet so there is enough context to improve it.")
            else:
                cleaned = draft.strip().rstrip(".")
                outcome = result.strip().rstrip(".")
                emphasis = f" using {role_context.strip()}" if role_context.strip() else ""
                versions = [
                    f"{cleaned}{emphasis}" + (f", resulting in {outcome}." if outcome else ". Add a verified outcome or metric if available."),
                    f"Delivered {cleaned[0].lower() + cleaned[1:]}{emphasis}" + (f"; {outcome}." if outcome else "; add the measurable impact if you can verify it."),
                ]
                st.session_state["toolkit_bullet_versions"] = versions
        for index, version in enumerate(st.session_state.get("toolkit_bullet_versions", []), start=1):
            st.text_area(f"Draft {index}", value=version, height=90, key=f"bullet_version_{index}")
        if st.session_state.get("toolkit_bullet_versions"):
            st.caption("Review every draft for accuracy. The coach does not invent achievements or metrics.")
            st.download_button("Download bullet drafts", "\n".join(st.session_state["toolkit_bullet_versions"]), file_name="resume_bullet_drafts.txt", mime="text/plain")

    with plan_tab:
        st.markdown("#### Plan a practical first 90 days")
        plan_role = st.text_input("Role", key="toolkit_plan_role", placeholder="e.g. Product analyst")
        plan_jd = st.text_area("Role priorities or job description", key="toolkit_plan_jd", height=130)
        if st.button("Create 30-60-90 day plan", type="primary", key="create_90_day_plan"):
            if not plan_role.strip():
                st.error("Enter a role to tailor the plan.")
            else:
                priorities = extract_skills(plan_jd)[:6]
                focus_line = ", ".join(priorities) if priorities else "the team's goals, tools, and customers"
                plan = (
                    f"# First 90 days as {plan_role.strip()}\n\n"
                    f"## Days 1–30 · Learn and align\n- Meet your manager, teammates, and key partners; agree on success measures.\n- Learn the product, workflows, tools, and current challenges around {focus_line}.\n- Review existing work and document questions, dependencies, and quick wins.\n\n"
                    f"## Days 31–60 · Contribute\n- Own a well-scoped task related to {focus_line}.\n- Share progress and risks early; request feedback on your approach.\n- Deliver one small improvement with a clear before-and-after measure.\n\n"
                    f"## Days 61–90 · Own and improve\n- Take responsibility for a larger deliverable aligned with team priorities.\n- Review outcomes with your manager and identify the next development goal.\n- Present a concise plan for the following quarter, grounded in observed evidence.\n\n"
                    "Customize these prompts with your manager; they are a starting point, not assumptions about the employer.\n"
                )
                st.session_state["toolkit_90_day_plan"] = plan
        if st.session_state.get("toolkit_90_day_plan"):
            st.markdown(st.session_state["toolkit_90_day_plan"])
            st.download_button("Download 30-60-90 plan", st.session_state["toolkit_90_day_plan"], file_name="30-60-90-day-plan.md", mime="text/markdown")

st.title("Career Compass", icon=":material/explore:")
st.caption("Practical tools for your next career move—from profile insights to interview practice.")

workspace_labels = ["Find jobs", "Hire candidates", "Career toolkit"]
workspace_icons = {
    "Find jobs": ":material/work:",
    "Hire candidates": ":material/groups:",
    "Career toolkit": ":material/auto_awesome:",
}
mode = st.segmented_control(
    "Choose a workspace",
    options=workspace_labels,
    format_func=lambda label: f"{workspace_icons[label]} {label}",
    default="Find jobs",
    key="workspace_navigation",
    width="stretch",
)

with st.sidebar:
    st.subheader("About Career Compass", anchor=False)
    st.write("Explore opportunities, review candidate evidence, and plan your next career steps.")
    st.caption("Resume analysis works locally. OpenAI and live job sources are optional and can be configured in `.env`.")

if mode == "Find jobs":
    st.header("Your job search", icon=":material/search:")
    st.caption("Upload your resume to see a profile summary and roles ranked by explainable skill and text matching.")
    left, right = st.columns([1, 1.45], gap="large")
    with left:
        resume = st.file_uploader("Upload your resume (PDF)", type=["pdf"], key="candidate_pdf")
        role = st.text_input("Target role", placeholder="e.g. Full Stack Developer")
        location = st.text_input(
            "Preferred location", value="Bengaluru",
            help="Used by configured Apify sources. Remotive listings show the countries each employer allows; check that field before applying.",
        )
        analyze = st.button("Analyze resume & find jobs", type="primary", width="stretch")
        if analyze:
            if not resume:
                st.error("Upload a PDF resume to continue.")
            elif not role.strip():
                st.error("Add a target role so recommendations can be ranked.")
            else:
                with st.spinner("Reading your resume and preparing career insights…"):
                    try:
                        text = extract_pdf_text(resume.name, resume.getvalue())
                        insights = analyze_resume(text, role)
                        st.session_state["candidate_text"] = text
                        st.session_state["insights"] = insights
                        st.session_state["target_role"] = role.strip()
                        st.session_state["target_location"] = location.strip()
                    except (ValueError, RuntimeError) as exc:
                        st.error(str(exc))
                if st.session_state.get("candidate_text"):
                    try:
                        with st.spinner("Searching configured job sources…"):
                            jobs, _ = fetch_jobs(role, location, int(os.getenv("APIFY_MAX_JOBS", "60")))
                            st.session_state["jobs"] = rank_jobs(jobs, st.session_state["candidate_text"], role)[:60]
                    except Exception as exc:
                        st.session_state["jobs"] = []
                        st.error(f"Job search failed: {exc}")
    with right:
        if "insights" not in st.session_state:
            st.markdown("### A clearer next step")
            st.markdown("Upload a text-based PDF resume and choose a role. Career Compass will extract your skills, suggest development priorities, and rank matching jobs.")
            st.info("Privacy: resume text is processed in memory. It is sent to OpenAI only when `OPENAI_API_KEY` is configured; otherwise analysis runs locally.")
        else:
            data = st.session_state["insights"]
            st.markdown("### Your profile snapshot")
            with st.container(border=True):
                st.markdown(data["summary"])
            st.caption(f"Analysis: {data.get('provider', 'Built-in analyzer')}")
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.markdown("#### Skills found")
                    st.metric("Recognized skills", len(data.get("skills", [])))
                    st.write(" · ".join(data.get("skills", [])) or "No known skills detected yet.")
            with c2:
                with st.container(border=True):
                    st.markdown("#### Skills to build")
                    st.metric("Priority areas", len(data.get("gaps", [])))
                    st.write(" · ".join(data.get("gaps", [])) or "No priority gaps identified.")
            with st.container(border=True):
                st.markdown("#### Suggested roadmap")
                for item in data.get("roadmap", []):
                    st.markdown(f"- {item}")
            with st.expander("Search keywords"):
                st.write(", ".join(data.get("keywords", [])))

    if "jobs" in st.session_state:
        st.divider()
        st.markdown("### Recommended opportunities")
        jobs = st.session_state["jobs"]
        if not jobs:
            st.info("No active listings matched this role. Try a broader target role, or configure another live job source in `.env`.")
        else:
            if any(job.get("source") == "Remotive" for job in jobs):
                st.info("Live remote vacancies from Remotive. Check each listing’s location eligibility before applying; feed entries may be delayed by up to 24 hours.")
            source_options = sorted({job.get("source", "Unknown") for job in jobs})
            filter_cols = st.columns([1, 1.4, 1.4])
            minimum_match = filter_cols[0].slider("Minimum match", 0, 100, 0, step=5, format="%d%%")
            selected_sources = filter_cols[1].multiselect("Sources", source_options, default=source_options)
            location_filter = filter_cols[2].text_input("Filter by location", placeholder="Any location")
            visible_jobs = [job for job in jobs
                            if job.get("match", 0) >= minimum_match
                            and job.get("source", "Unknown") in selected_sources
                            and location_filter.casefold() in job.get("location", "").casefold()]
            st.caption(f"Showing {len(visible_jobs)} of {len(jobs)} recommendations")
            job_export = []
            for job in visible_jobs:
                details = job["match_details"]
                components = details["components"]
                job_export.append({
                    "title": job.get("title", ""), "company": job.get("company", ""),
                    "location": job.get("location", ""), "source": job.get("source", ""),
                    "match_score": job.get("match", 0),
                    "required_skill_coverage": components["required_skill_coverage"],
                    "preferred_skill_coverage": components["preferred_skill_coverage"],
                    "text_similarity": components["text_similarity"],
                    "role_title_fit": components["role_title_fit"],
                    "matched_required_skills": details["matched_required"],
                    "missing_required_skills": details["missing_required"],
                    "salary": job.get("salary", ""),
                    "published": job.get("publication_date", ""),
                    "url": job.get("url", ""),
                })
            st.download_button(
                "Download filtered jobs (CSV)",
                data=csv_download(job_export, list(job_export[0]) if job_export else [
                    "title", "company", "location", "source", "match_score", "url"
                ]),
                file_name="career_compass_job_recommendations.csv",
                mime="text/csv",
                icon=":material/download:",
                disabled=not job_export,
            )
        missing_skills = sorted({skill for job in jobs
                                 for skill in job["match_details"]["missing_required"]})
        scenario_options = ["No hypothetical skill"] + missing_skills
        simulated_skill = st.selectbox(
            "What if you gained or demonstrated one skill?",
            scenario_options,
            help="This scenario changes skill coverage only. It does not edit your resume or claim you have the skill.",
            key=f"what_if_skill_{abs(hash(tuple(scenario_options)))}",
        )
        scenario_lookup = {}
        if simulated_skill != "No hypothetical skill":
            scenario_jobs = rank_jobs(
                [dict(job) for job in jobs],
                st.session_state["candidate_text"],
                st.session_state.get("target_role", ""),
                simulated_skills=[simulated_skill],
            )
            scenario_lookup = {(job.get("title"), job.get("company")): job for job in scenario_jobs}
            st.info(f"Hypothetical scenario: treating **{simulated_skill}** as demonstrated for scoring. Your uploaded resume remains unchanged.")
        saved_ids = {saved["job_id"] for saved in list_saved_jobs()}
        for job in visible_jobs if jobs else []:
            title = job.get("title", "Role")
            company = job.get("company", "Company")
            url = job.get("url", "")
            scenario_job = scenario_lookup.get((title, company))
            delta = (scenario_job["match"] - job["match"]) if scenario_job else None
            with st.container(border=True):
                a, b, c = st.columns([4, 1, 1.5])
                a.markdown(f"**{title}**  \n{company} · {job.get('location', 'Location not listed')} · {job.get('source', '')}")
                b.metric("Explainable match", f"{job.get('match', 0)}%",
                         delta=f"{delta:+.1f} points" if delta is not None else None)
                job_metadata = [value for value in [job.get("job_type"), job.get("salary")] if value]
                if job.get("publication_date"):
                    job_metadata.append("Posted " + job["publication_date"][:10])
                if job_metadata:
                    a.caption(" · ".join(job_metadata))
                if job.get("description"):
                    st.caption(job["description"][:380] + ("…" if len(job["description"]) > 380 else ""))
                if url:
                    if job.get("source") == "Remotive":
                        a.link_button("View live listing on Remotive", url, icon=":material/open_in_new:")
                    else:
                        a.link_button("View live listing", url, icon=":material/open_in_new:")
                identifier = job_key(job)
                is_saved = identifier in saved_ids
                if c.button("Remove saved" if is_saved else "Save job", key=f"shortlist_{identifier}"):
                    if is_saved:
                        remove_job(identifier)
                    else:
                        save_job(job)
                    st.rerun()
                with st.expander(f"Why this match: {title}", key=f"match_expander_{identifier}"):
                    render_match_explanation(job["match_details"])

        st.divider()
        st.markdown("### Shortlist and application tracker")
        saved_jobs = list_saved_jobs()
        if not saved_jobs:
            st.info("Save a recommendation to track its application progress here. Your shortlist is stored locally on this machine.")
        else:
            tracker_rows = [{key: row[key] for key in (
                "title", "company", "location", "source", "match_score", "status", "notes", "url", "updated_at"
            )} for row in saved_jobs]
            st.download_button(
                "Export application tracker (CSV)",
                data=csv_download(tracker_rows, list(tracker_rows[0])),
                file_name="career_compass_application_tracker.csv",
                mime="text/csv",
                icon=":material/download:",
            )
            for row in saved_jobs:
                with st.container(border=True):
                    st.markdown(f"**{row['title']}** · {row['company']} · {row['location']}")
                    if row["url"]:
                        st.link_button("Open listing", row["url"])
                    with st.form(f"application_{row['job_id']}"):
                        status_col, notes_col = st.columns([1, 2])
                        status = status_col.selectbox(
                            "Application status", APPLICATION_STATUSES,
                            index=APPLICATION_STATUSES.index(row["status"]),
                            key=f"status_{row['job_id']}",
                        )
                        notes = notes_col.text_area(
                            "Notes", value=row["notes"], max_chars=4000,
                            key=f"notes_{row['job_id']}",
                        )
                        submitted = st.form_submit_button("Save tracker update", icon=":material/save:")
                    if submitted:
                        update_job(row["job_id"], status, notes)
                        st.success("Application tracker updated.")
                    if st.button("Remove from tracker", key=f"delete_{row['job_id']}"):
                        remove_job(row["job_id"])
                        st.rerun()
elif mode == "Hire candidates":
    st.header("Candidate review", icon=":material/groups:")
    st.caption("Compare resume evidence with role requirements. Scores support human review and do not make hiring decisions.")
    role_title = st.text_input("Role title (optional)", placeholder="e.g. Full Stack Developer",
                               help="Adds role wording to the text-overlap comparison.")
    description = st.text_area("Job description", height=190, placeholder="Paste responsibilities, qualifications, and required skills…")
    resumes = st.file_uploader("Upload candidate resumes (PDF, multiple allowed)", type=["pdf"], accept_multiple_files=True)
    if st.button("Rank candidates", type="primary"):
        if len(description.strip()) < 30:
            st.error("Add a fuller job description before matching candidates.")
        elif not resumes:
            st.error("Upload at least one candidate resume.")
        else:
            rows = []
            for uploaded in resumes:
                try:
                    text = extract_pdf_text(uploaded.name, uploaded.getvalue())
                    details = score_match(text, description, context_text=role_title)
                    rows.append({"name": uploaded.name,
                                 "match": details["match"], "details": details,
                                 "skills": extract_skills(text)})
                except ValueError as exc:
                    st.warning(f"{uploaded.name}: {exc}")
            st.session_state["candidate_matches"] = sorted(rows, key=lambda row: row["match"], reverse=True)
    candidate_matches = st.session_state.get("candidate_matches", [])
    if candidate_matches:
        minimum_candidate_match = st.slider("Minimum candidate match", 0, 100, 0, step=5, format="%d%%")
        visible_candidates = [row for row in candidate_matches if row["match"] >= minimum_candidate_match]
        st.caption(f"Showing {len(visible_candidates)} of {len(candidate_matches)} candidates")
        candidate_export = []
        for row in visible_candidates:
            details = row["details"]
            components = details["components"]
            candidate_export.append({
                "resume_file": row["name"], "match_score": row["match"],
                "required_skill_coverage": components["required_skill_coverage"],
                "preferred_skill_coverage": components["preferred_skill_coverage"],
                "text_similarity": components["text_similarity"],
                "detected_skills": row["skills"],
                "matched_required_skills": details["matched_required"],
                "missing_required_skills": details["missing_required"],
                "matched_preferred_skills": details["matched_preferred"],
                "missing_preferred_skills": details["missing_preferred"],
            })
        st.download_button(
            "Download candidate review (CSV)",
            data=csv_download(candidate_export, list(candidate_export[0]) if candidate_export else [
                "resume_file", "match_score", "required_skill_coverage", "detected_skills"
            ]),
            file_name="career_compass_candidate_review.csv",
            mime="text/csv",
            icon=":material/download:",
            disabled=not candidate_export,
        )
    else:
        visible_candidates = []
    for index, row in enumerate(visible_candidates, start=1):
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{index}. {row['name']}**")
            c2.metric("Explainable match", f"{row['match']}%")
            st.caption("Detected skills: " + (", ".join(row["skills"]) if row["skills"] else "No recognized skills"))
            st.caption("Skills not found means no matching evidence was extracted from the resume text; it does not prove the candidate lacks that skill.")
            with st.expander(f"Explain match for {row['name']} ({index})", key=f"candidate_explanation_{index}_{row['name']}"):
                render_match_explanation(row["details"])
else:
    st.header("Career toolkit", icon=":material/auto_awesome:")
    st.caption("Practice interviews, improve resume bullets, and plan a strong first 90 days.")
    render_career_toolkit()

st.caption("Career Compass · Resume text and match scores are advisory. Review results with human judgment.")
