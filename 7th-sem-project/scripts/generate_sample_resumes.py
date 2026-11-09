"""Generate fictional PDF resumes for the Career Compass demo workflows."""

from __future__ import annotations

import re
from zipfile import ZIP_DEFLATED, ZipFile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1] / "samples"

PROFESSIONALS = [
    ("Aarav Mehta", "Software Engineer", "Bengaluru, India", "Python, Java, FastAPI, PostgreSQL, Docker, AWS, Git, REST APIs", "Software Engineer Intern · 2024-2025", "Built internal APIs used by 3 product teams; reduced report generation time by 28%.", "B.Tech Computer Science · 2025"),
    ("Diya Nair", "Data Analyst", "Kochi, India", "SQL, Python, Excel, Power BI, Tableau, statistics, data visualization", "Data Analyst Intern · 2024-2025", "Automated weekly reporting and built dashboards for sales and operations stakeholders.", "B.Sc Statistics · 2025"),
    ("Kabir Shah", "Frontend Developer", "Pune, India", "JavaScript, TypeScript, React, HTML, CSS, accessibility, Git, REST APIs", "Frontend Developer Intern · 2024-2025", "Shipped responsive product pages and improved Lighthouse accessibility scores.", "B.Tech Information Technology · 2025"),
    ("Mira Iyer", "Machine Learning Engineer", "Chennai, India", "Python, PyTorch, scikit-learn, NLP, pandas, SQL, model evaluation", "ML Research Assistant · 2024-2025", "Compared text classification approaches and documented reproducible experiments.", "M.Tech Data Science · 2025"),
    ("Rohan Das", "Backend Developer", "Bhubaneswar, India", "Java, Spring Boot, PostgreSQL, REST APIs, Docker, Linux, Git", "Backend Intern · 2024-2025", "Implemented API validation and database migrations for a student services platform.", "B.Tech Computer Science · 2025"),
    ("Ananya Rao", "Product Analyst", "Hyderabad, India", "SQL, Excel, Python, Tableau, experimentation, communication, Agile", "Product Operations Intern · 2024-2025", "Prepared product usage analysis and summarized customer feedback themes.", "BBA Business Analytics · 2025"),
    ("Ishaan Kapoor", "Cloud Engineer", "Gurugram, India", "AWS, Azure, Docker, Kubernetes, Linux, Python, Terraform, monitoring", "Cloud Support Intern · 2024-2025", "Created deployment runbooks and automated routine environment checks.", "B.Tech Information Technology · 2025"),
    ("Tara Banerjee", "UX Researcher", "Kolkata, India", "user research, usability testing, Figma, accessibility, interviews, analysis", "UX Research Intern · 2024-2025", "Synthesized moderated usability sessions into prioritized design recommendations.", "B.Des Interaction Design · 2025"),
    ("Neil Fernandes", "Cybersecurity Analyst", "Mumbai, India", "Python, Linux, networking, SIEM, vulnerability assessment, incident response", "Security Operations Intern · 2024-2025", "Triaged simulated alerts and wrote clear incident notes for escalation.", "B.Sc Information Security · 2025"),
    ("Sana Qureshi", "Marketing Analyst", "Delhi, India", "Excel, SQL, Google Analytics, Tableau, campaign analysis, communication", "Marketing Intern · 2024-2025", "Tracked campaign performance and presented weekly audience insights.", "BA Economics · 2025"),
    ("Dev Patel", "Data Scientist", "Ahmedabad, India", "Python, machine learning, pandas, SQL, scikit-learn, statistics, NLP", "Data Science Intern · 2024-2025", "Built a baseline demand forecasting model and explained its limitations.", "M.Sc Applied Mathematics · 2025"),
    ("Leela Menon", "Mobile App Developer", "Thiruvananthapuram, India", "Kotlin, Android, Java, REST APIs, SQLite, Git, UI testing", "Android Developer Intern · 2024-2025", "Developed app screens and integrated API responses with loading and error states.", "B.Tech Computer Science · 2025"),
    ("Arjun Sen", "QA Automation Engineer", "Jaipur, India", "Python, Selenium, pytest, API testing, SQL, Git, test planning", "QA Intern · 2024-2025", "Added regression checks for critical user journeys and improved issue reproduction notes.", "BCA · 2025"),
    ("Nisha Verma", "HR Operations Analyst", "Noida, India", "Excel, Power BI, data analysis, communication, process documentation", "People Operations Intern · 2024-2025", "Organized anonymized onboarding metrics and documented workflow improvements.", "MBA Human Resources · 2025"),
    ("Vihaan Kulkarni", "DevOps Engineer", "Nashik, India", "Docker, Kubernetes, GitHub Actions, AWS, Linux, Python, monitoring", "DevOps Intern · 2024-2025", "Maintained CI workflows and documented deployment checks for a class project.", "B.Tech Information Technology · 2025"),
    ("Zoya Ali", "Technical Writer", "Lucknow, India", "technical writing, API documentation, Markdown, Git, research, communication", "Documentation Intern · 2024-2025", "Reworked setup guides after interviewing developers about common onboarding issues.", "BA English · 2025"),
    ("Aditya Bose", "Business Intelligence Analyst", "Indore, India", "SQL, Power BI, DAX, Excel, data modeling, stakeholder communication", "BI Intern · 2024-2025", "Designed an operations dashboard with clear definitions for core measures.", "B.Com · 2025"),
    ("Kiara Sethi", "AI Product Associate", "Chandigarh, India", "LLM, prompt evaluation, Python, user research, product analytics, Agile", "AI Product Intern · 2024-2025", "Compared assistant outputs against a rubric and summarized recurring failure patterns.", "B.Tech Computer Science · 2025"),
    ("Reyansh Ghosh", "Game Developer", "Kolkata, India", "C#, Unity, gameplay prototyping, Git, debugging, 3D math", "Game Development Intern · 2024-2025", "Built a playable prototype and tuned controls based on structured playtests.", "B.Sc Computer Science · 2025"),
    ("Myra Thomas", "Project Coordinator", "Mysuru, India", "Agile, Jira, Excel, communication, risk tracking, documentation", "Project Coordinator Intern · 2024-2025", "Maintained project actions and produced concise weekly status summaries.", "BBA · 2025"),
]

# Employer matcher examples target the sample description below. The set deliberately
# ranges from closely related full-stack experience to adjacent and unrelated profiles.
EMPLOYER_CANDIDATES = [
    ("Riya Malhotra", "Bengaluru", "Full Stack Developer", "React, TypeScript, Node.js, Express, PostgreSQL, REST APIs, AWS, Docker, Git, testing", "Full Stack Engineer · 2023-2025", "Delivered customer-facing React features and Node APIs; improved page load time by 35%.", "B.Tech Computer Science · 2023"),
    ("Karan Desai", "Pune", "Software Engineer", "JavaScript, React, Node.js, MongoDB, REST APIs, Git, Docker, CI/CD, AWS", "Software Engineer · 2022-2025", "Built and maintained full-stack workflows for a subscription product with 20,000 users.", "B.E. Information Technology · 2022"),
    ("Meera Krishnan", "Chennai", "Web Application Developer", "React, JavaScript, TypeScript, Python, FastAPI, PostgreSQL, HTML, CSS, Git", "Web Developer · 2023-2025", "Created responsive interfaces and integrated API endpoints for an internal operations suite.", "B.Tech Computer Science · 2023"),
    ("Siddharth Jain", "Hyderabad", "Backend Engineer", "Node.js, Express, TypeScript, PostgreSQL, REST APIs, Docker, AWS, Redis, Git", "Backend Engineer · 2022-2025", "Designed versioned services and database migrations; partnered with frontend engineers.", "B.Tech Software Engineering · 2022"),
    ("Aisha Khan", "Delhi", "Frontend Engineer", "React, TypeScript, JavaScript, HTML, CSS, accessibility, testing, Git, REST APIs", "Frontend Engineer · 2023-2025", "Shipped accessible interfaces and reusable components for web applications.", "B.Des and Web Technology · 2023"),
    ("Manav Reddy", "Bengaluru", "Full Stack Developer", "Vue.js, JavaScript, Node.js, PostgreSQL, REST APIs, Docker, Git, unit testing", "Associate Developer · 2024-2025", "Built admin screens and API routes; contributed bug fixes and integration tests.", "BCA · 2024"),
    ("Pooja Mukherjee", "Kolkata", "Application Developer", "React, JavaScript, Java, Spring Boot, MySQL, REST APIs, Git, Agile", "Application Developer · 2022-2025", "Delivered React and Java features for a customer service platform.", "MCA · 2022"),
    ("Rahul Bhat", "Mumbai", "Full Stack Engineer", "Angular, TypeScript, Node.js, MongoDB, AWS, Docker, Git, REST APIs, SQL", "Full Stack Engineer · 2021-2025", "Supported deployments and developed web modules across frontend and backend.", "B.E. Computer Engineering · 2021"),
    ("Ira Chatterjee", "Remote, India", "Frontend Developer", "React, TypeScript, Next.js, JavaScript, HTML, CSS, API integration, Git", "Frontend Developer · 2023-2025", "Implemented responsive pages and collaborated with API and design teams.", "B.Tech Information Technology · 2023"),
    ("Aman Sood", "Jaipur", "Junior Software Developer", "JavaScript, React, Node.js, Express, MongoDB, HTML, CSS, Git", "Developer Intern · 2024-2025", "Built a full-stack capstone application with authentication and CRUD workflows.", "B.Tech Computer Science · 2025"),
    ("Sana Pillai", "Kochi", "Software Engineer", "Python, Django, PostgreSQL, REST APIs, React basics, Docker, Git, Linux", "Software Engineer · 2022-2025", "Developed Django services and supported a small React dashboard integration.", "B.Tech Computer Science · 2022"),
    ("Yash Arora", "Noida", "Web Developer", "PHP, Laravel, MySQL, JavaScript, HTML, CSS, Git, REST APIs", "Web Developer · 2022-2025", "Maintained business websites and built internal CRUD tools for customer support.", "BCA · 2022"),
    ("Tanya Ghosh", "Bhubaneswar", "Data Analyst", "Python, SQL, Excel, Power BI, Tableau, statistics, data visualization", "Data Analyst · 2023-2025", "Created dashboards and performed cohort analysis for business stakeholders.", "M.Sc Statistics · 2023"),
    ("Arnav Gupta", "Gurugram", "Cloud Support Engineer", "AWS, Linux, Docker, Kubernetes, Python, monitoring, incident response", "Cloud Support Associate · 2022-2025", "Resolved cloud service incidents and maintained deployment runbooks.", "B.Tech Electronics · 2022"),
    ("Nandini Shetty", "Mysuru", "UX Designer", "Figma, user research, wireframing, usability testing, accessibility, prototyping", "UX Designer · 2023-2025", "Designed and tested user flows for mobile and web products.", "B.Des Interaction Design · 2023"),
    ("Farhan Mirza", "Lucknow", "QA Engineer", "Selenium, Python, pytest, API testing, SQL, test planning, Git", "QA Engineer · 2022-2025", "Created automated regression tests for web workflows and APIs.", "B.Tech Information Technology · 2022"),
    ("Lavanya Rao", "Hyderabad", "Product Manager", "product strategy, roadmap, Agile, user research, analytics, communication", "Associate Product Manager · 2022-2025", "Coordinated product launches and synthesized user feedback into requirements.", "MBA · 2022"),
    ("Kabir Chawla", "Pune", "Electrical Engineer", "embedded systems, C, PCB design, MATLAB, testing, technical documentation", "Graduate Engineer Trainee · 2023-2025", "Supported hardware validation and wrote test reports for embedded devices.", "B.E. Electrical Engineering · 2023"),
    ("Simran Kaur", "Amritsar", "Marketing Associate", "campaign planning, Excel, Google Analytics, content strategy, communication", "Marketing Associate · 2022-2025", "Coordinated digital campaigns and summarized performance reports.", "BA Communications · 2022"),
    ("Devika Nambiar", "Thiruvananthapuram", "Graduate Trainee", "Excel, communication, documentation, teamwork, problem solving", "Graduate Trainee · 2024-2025", "Completed cross-functional rotations and documented a process improvement project.", "B.Com · 2024"),
]

SAMPLE_JD = """Sample role: Full Stack Developer (early career)\n\nLocation: Bengaluru or hybrid\n\nWe are looking for an early-career developer to build and improve customer-facing web products. The role works across a React and TypeScript frontend and Node.js services, with PostgreSQL data storage.\n\nResponsibilities\n- Build accessible, responsive UI features with React and TypeScript.\n- Develop and integrate REST APIs using Node.js and Express.\n- Work with PostgreSQL schemas and write reliable queries.\n- Add tests, review code, and collaborate through Git-based workflows.\n- Participate in deployments and basic cloud operations on AWS or Docker.\n\nPreferred qualifications\n- 0-3 years of relevant experience, internships, or substantial project work.\n- Understanding of JavaScript, API design, SQL, and software testing.\n- Clear communication and a collaborative approach.\n\nSynthetic demonstration text only; not a real vacancy."""


def safe_filename(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def build_pdf(path: Path, name: str, title: str, city: str, skills: str,
              experience: str, achievement: str, education: str, index: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CandidateName", parent=styles["Title"], fontName="Helvetica-Bold",
                              fontSize=20, leading=23, alignment=TA_CENTER, textColor=colors.HexColor("#12324A"), spaceAfter=2))
    styles.add(ParagraphStyle(name="Role", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10.5,
                              leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#16727A"), spaceAfter=2))
    styles.add(ParagraphStyle(name="Contact", parent=styles["Normal"], fontSize=8.3, leading=10,
                              alignment=TA_CENTER, textColor=colors.HexColor("#5B6C7D"), spaceAfter=7))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10,
                              leading=12, textColor=colors.HexColor("#155E75"), spaceBefore=5, spaceAfter=3))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=8.8, leading=11.5,
                              alignment=TA_LEFT, textColor=colors.HexColor("#263746"), spaceAfter=2))
    styles.add(ParagraphStyle(name="Banner", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5,
                              leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#8A4B08")))
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=.62*inch, leftMargin=.62*inch,
                            topMargin=.42*inch, bottomMargin=.45*inch, title=f"Synthetic Resume - {name}",
                            author="Career Compass Sample Data Generator")
    story = [Paragraph("SYNTHETIC SAMPLE RESUME · NOT A REAL PERSON", styles["Banner"]), Spacer(1, 4),
             Paragraph(name, styles["CandidateName"]), Paragraph(title, styles["Role"]),
             Paragraph(f"{city} &nbsp; | &nbsp; {name.split()[0].lower()}.{name.split()[-1].lower()}@example.invalid &nbsp; | &nbsp; Portfolio: example.invalid/{index}", styles["Contact"])]
    def section(label: str, content: str) -> None:
        story.append(Paragraph(label.upper(), styles["Section"]))
        story.append(Paragraph(content.replace("&", "&amp;"), styles["BodySmall"]))
    section("Professional Summary", f"Early-career {title.lower()} with hands-on project and internship experience. Interested in building reliable, user-focused solutions and continuing to grow through collaborative work.")
    section("Technical Skills", skills)
    story.append(Paragraph("EXPERIENCE", styles["Section"]))
    story.append(Paragraph(f"<b>{experience}</b>", styles["BodySmall"]))
    story.append(Paragraph(achievement, styles["BodySmall"]))
    section("Selected Project", f"{title} portfolio project · 2024-2025. Applied {', '.join(skills.split(', ')[:4])} to solve a practical workflow problem; documented decisions and next steps.")
    section("Education", education)
    section("Additional", "Languages: English and one regional language · Work authorization: India · References available on request")
    doc.build(story)


def main() -> None:
    dirs = {"professional": ROOT / "professional_job_search", "employer": ROOT / "employer_resume_match"}
    for index, record in enumerate(PROFESSIONALS, 1):
        name, title, city, skills, experience, achievement, education = record
        build_pdf(dirs["professional"] / f"professional_{index:02d}_{safe_filename(name)}.pdf",
                  name, title, city, skills, experience, achievement, education, f"p{index:02d}")
    for index, record in enumerate(EMPLOYER_CANDIDATES, 1):
        name, city, title, skills, experience, achievement, education = record
        build_pdf(dirs["employer"] / f"candidate_{index:02d}_{safe_filename(name)}.pdf",
                  name, title, city, skills, experience, achievement, education, f"e{index:02d}")
    (dirs["employer"] / "sample_job_description.txt").write_text(SAMPLE_JD, encoding="utf-8")
    for label, directory in dirs.items():
        pdfs = sorted(directory.glob("*.pdf"))
        lines = [f"{label.replace('_', ' ').title()} sample set", "", "All names and experience details are fictional.", ""]
        lines.extend(path.name for path in pdfs)
        (directory / "INDEX.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        with ZipFile(ROOT / f"{label}_samples.zip", "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(directory.iterdir()):
                if path.is_file():
                    archive.write(path, arcname=f"{directory.name}/{path.name}")
    total = sum(len(list(directory.glob("*.pdf"))) for directory in dirs.values())
    print(f"Generated {total} sample resumes under {ROOT}")


if __name__ == "__main__":
    main()
