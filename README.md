```

---

## 🤖 Pipeline Workflow

1.  **Scrape:** Queries defined roles (e.g., "Machine Learning Intern") across major job boards.
2.  **Parse:** Extracts metadata and normalizes stipends (e.g., converting "3-7 LPA" to "₹25,000/month").
3.  **Filter:** Drops listings below your `MIN_STIPEND` threshold.
4.  **Store:** Performs an `UPSERT` into SQLite to avoid duplicate notifications.
5.  **Digest:** Generates a beautiful HTML summary and a professional PDF attachment.
6.  **Notify:** Fires an email to your inbox and marks listings as "notified".

---

## 🤝 Contributing

This project was built to help students secure high-stipend internships. If you have ideas for new sources or better parsing logic, feel free to fork and submit a PR!

**License:** MIT  
**AuthorHere is a professional and comprehensive README for your project.

---

# 🚀 InternHunter AI

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B.svg)](https://internhunterai-aryandhanuka10.streamlit.app/)

**InternHunter AI** is an automated internship discovery engine designed for engineering students. It eliminates the manual "apply-to-everything" grind by searching the web daily, parsing high-quality opportunities using AI, and delivering a curated digest straight to your inbox with ready-to-use cold email drafts.

**🔗 Frontend URL:** [internhunterai-aryandhanuka10.streamlit.app](https://internhunterai-aryandhanuka10.streamlit.app/)

---

## ✨ Key Features

*   **🔍 Multi-Source Scraper:** Aggregates listings from LinkedIn, Internshala, Unstop, Wellfound, and more via Google Serper API.
*   **🧠 Intelligent Parser:** Uses regex and logic to extract structured data (stipend, deadline, location) from messy search snippets.
*   **🎯 Smart Scoring:** Ranks internships based on stipend amounts, preferred locations, and source credibility.
*   **📧 Automated Digests:** Sends a daily HTML and PDF digest to your Gmail with professional formatting.
*   **✍️ Cold Email Generator:** Automatically drafts personalized cold emails for every opportunity, referencing your specific skills and college.
*   **🤝 Referral Finder:** Generates one-click LinkedIn search links to find alumni from your college (e.g., Bennett University) currently working at the hiring company.
*   **📊 Web Dashboard:** A sleek Streamlit-powered frontend with "Cloud" and "Local" modes to track applications and run pipelines.

---

## 🛠️ Tech Stack

*   **Backend:** Python, FastAPI
*   **Frontend:** Streamlit (Custom CSS with Glassmorphism/Dark Mode)
*   **Database:** SQLite (Relational storage with migration support)
*   **Automation:** GitHub Actions (Cron: 9:30 AM IST Daily)
*   **APIs:** Serper (Google Search), OpenAI (Email Drafting)
*   **Reporting:** ReportLab (PDF Generation), SMTP (Gmail Integration)

---

## 🚀 Setup Guide

### 1. Prerequisites
*   Python 3.11 or higher
*   A [Serper API Key](https://serper.dev/) (Free tier provides 2,500 searches)
*   A Gmail [App Password](https://myaccount.google.com/apppasswords) (for the Mailer)

### 2. Installation
```bash
# Clone the repository
git clone [https://github.com/AryanDhanuka10/InternHunter_AI.git](https://github.com/AryanDhanuka10/InternHunter_AI.git)
cd InternHunter_AI

# Run the scaffold script to create directory structure
python template.py

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory (referencing `.env.example`):
```ini
USER_NAME=Aryan Dhanuka
USER_EMAIL=your-email@gmail.com
USER_COLLEGE=Bennett University
SERPER_API_KEY=your_serper_api_key
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASS=your_16_char_app_password
```

### 4. Running InternHunter
**Manual Pipeline Run:**
```bash
python -m internhunter.scheduler
```

**Launch Dashboard:**
```bash
streamlit run dashboard.py
```

**Launch API Server:**
```bash
uvicorn app.main:app --reload
```

---

## 📂 Project Structure

```text
├── app/                # FastAPI Backend Routers
├── internhunter/       # Core Logic (Scraper, Parser, Mailer)
├── data/               # SQLite DB and Generated Digests (PDF/HTML)
├── logs/               # Execution logs
├── tests/              # Pytest suite (Smoke & Interactive tests)
├── dashboard.py        # Streamlit Frontend
└── Dockerfile          # Deployment config for HF Spaces
```

---

## 🤖 Pipeline Workflow

1.  **Scrape:** Queries defined roles (e.g., "Machine Learning Intern") across major job boards.
2.  **Parse:** Extracts metadata and normalizes stipends (e.g., converting "3-7 LPA" to "₹25,000/month").
3.  **Filter:** Drops listings below your `MIN_STIPEND` threshold.
4.  **Store:** Performs an `UPSERT` into SQLite to avoid duplicate notifications.
5.  **Digest:** Generates a beautiful HTML summary and a professional PDF attachment.
6.  **Notify:** Fires an email to your inbox and marks listings as "notified".

---

## 🤝 Contributing

This project was built to help students secure high-stipend internships. If you have ideas for new sources or better parsing logic, feel free to fork and submit a PR!

**License:** MIT  
**Author:** [Aryan Dhanuka](https://github.com/AryanDhanuka10)
```