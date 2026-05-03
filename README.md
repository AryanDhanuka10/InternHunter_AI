# 🚀 InternHunter AI

**InternHunter AI** is an automated internship discovery engine designed for engineering students. It eliminates the "manual refresh" fatigue by searching the web daily, parsing key details (stipends, deadlines, locations), and delivering high-quality leads straight to your inbox and a glassmorphism-inspired dashboard.

**🌐 Live Frontend:** [internhunterai-aryandhanuka10.streamlit.app](https://internhunterai-aryandhanuka10.streamlit.app/).

**🌐 Live Backend:** [aryandhanuka10-internhunter-api.hf.space/docs](https://aryandhanuka10-internhunter-api.hf.space/docs).

---

## ✨ Key Features

*   **🔍 Multi-Source Scraper:** Aggregates listings from LinkedIn, Internshala, Unstop, Wellfound, and more using the Serper API.
*   **🧠 Intelligent Parsing:** Uses regex-based logic to extract stipends (handling Lacs, LPA, and k-notation), deadlines, and locations from unstructured snippets.
*   **📊 Lead Scoring:** Ranks internships based on stipend amount, preferred locations, and source credibility.
*   **📧 Daily Digest:** Sends a beautiful HTML and PDF summary of new opportunities to your Gmail every morning.
*   **🤝 Referral Finder:** Automatically generates LinkedIn search queries to find alumni from your college working at the hiring companies.
*   **💻 Dark-Mode Dashboard:** A sleek Streamlit frontend to track applications, filter by role, and preview cold emails.
*   **🤖 GitHub Actions Integration:** Runs the full pipeline every day at 9:30 AM IST for free.

---

## 🏗️ Project Architecture

```bash
├── app/                  # FastAPI Backend (Routers for opportunities, profile, actions)
├── internhunter/         # Core Logic (Scraper, Parser, Database, Mailer, Scheduler)
├── data/                 # SQLite DB and local storage for digests
├── assets/               # Resume and static files
├── tests/                # Comprehensive PyTest suite
├── dashboard.py          # Streamlit Frontend
└── scheduler.py          # Pipeline Orchestrator
```

---

## 🛠️ Setup & Installation

### 1. Clone & Scaffold
```bash
git clone https://github.com/yourusername/InternHunter_AI.git
cd InternHunter_AI
python template.py  # Scaffolds the project structure
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file from the example:
```bash
cp .env.example .env
```
Fill in the following keys:
*   `SERPER_API_KEY`: Get one at [serper.dev](https://serper.dev).
*   `GMAIL_USER`: Your Gmail address.
*   `GMAIL_APP_PASS`: 16-character App Password (Security > App Passwords in Google Account).
*   `USER_COLLEGE`: Used for finding alumni referrals.

### 4. Run the Pipeline
Execute the full scrape-parse-notify cycle:
```bash
python -m internhunter.scheduler
```

### 5. Launch the Dashboard
```bash
streamlit run dashboard.py
```

---

## 🚀 Deployment

### Backend (FastAPI)
The backend is Docker-ready and can be deployed to **Hugging Face Spaces** or any VPS.
```bash
docker build -t internhunter-api .
docker run -p 7860:7860 internhunter-api
```

### Automation (GitHub Actions)
The project includes a `.github/workflows/daily.yml` file. Simply:
1. Push the code to GitHub.
2. Add your `.env` variables to **Settings > Secrets and Variables > Actions**.
3. The "Hunt" will run automatically every day at 04:00 UTC (9:30 AM IST).

---

## 📊 Pipeline Logic

| Stage | Logic |
| :--- | :--- |
| **Scrape** | Queries Serper API for roles like "Machine Learning Intern" |
| **Parse** | Extracts `₹1,10,000/month` from snippets like "1.1 Lacs per month" |
| **Filter** | Drops listings below `MIN_STIPEND` (default ₹10,000) |
| **Score** | Awards points for "Remote" or "Bangalore" locations |
| **Notify** | Generates HTML Digest + PDF and emails them via SMTP |

---

## 📄 License
Distributed under the **MIT License**. See `LICENSE` for more information.

**Built with ❤️ by [Aryan Dhanuka](https://github.com/AryanDhanuka10)**


