# TECHBLITZ — Online Assessment Platform
> **Smart Browser-Monitored Online Test System**

A modern, production-ready, browser-monitored online assessment platform designed for college coding club competitions and campus hiring drives where hundreds of candidates take exams simultaneously.

---

## 🚀 Key Features

- **Strict Access Control**: Candidate authentication requires matching **Hall Ticket Number + Name + Team ID** against the Admin Registration Database. Unregistered candidates cannot create their own accounts or access tests.
- **Drag-and-Drop Registration Import**: Upload Excel (`.xlsx`) or CSV files directly into the admin panel with automated fuzzy column detection, interactive column mapping, validation preview, and duplicate handling (`Skip`, `Update`, `Keep`).
- **Server-Authoritative Timing**: Test duration and countdowns are calculated and enforced by the server, preventing client-side timer manipulation or clock drift.
- **Browser Proctoring Engine**:
  - Detects **Tab Switching** (`Page Visibility API`)
  - Detects **Window Blur / Leaving Exam Screen**
  - Detects **Fullscreen Exits**
  - Blocks and logs **Copy, Paste, and Cut** attempts
  - Restricts **Right-Click Context Menus** and inspection shortcuts (`F12`, `Ctrl+Shift+I`)
  - Built-in debouncing to avoid redundant violation spam.
- **20-Second Violation Acknowledgement Rule**:
  - Every detected violation pauses candidate interaction and triggers an overlay modal with an urgent 20-second countdown.
  - If the candidate clicks **[ OK ]** within 20 seconds, the test resumes.
  - If 20 seconds elapse without acknowledgement, the system **automatically blocks the candidate**, disables all questions, notifies the proctor, and puts the candidate in a waiting screen.
- **Admin Violation Center**:
  - Live proctoring dashboard updated every 2.5 seconds.
  - Real-time violation alert feed.
  - Deep candidate profile inspection showing full strike history and question responses.
  - One-click proctoring interventions: **Grant Permission**, **Unblock**, **Manual Block**, and **Terminate Test**.
- **Question Generator & Review**:
  - Generate MCQs by topic (15+ technical categories like DSA, Python, DBMS, OS, Networks, Aptitude) and difficulty.
  - Pluggable AI provider (`OpenAI`, `Gemini`, or built-in curated question bank that works 100% offline).
  - Pre-publication review table where admins can edit question text, options, marks, and set correct answers.
- **20-Minute Assessment Window**: Pre-configured with a server-enforced **20-minute** exam duration and real-time synchronization.
- **Admin-Only Final Score Privacy**: Final scores, percentages, and marks are hidden from the candidate portal upon submission and are exclusively visible to administrators on the dashboard, candidate profiles, and exported Excel report.
- **Live Rankings & Excel Export**:
  - Real-time leaderboards sorted by **Highest Score → Lowest Score** with earlier submission tie-breaking.
  - Export official formatted spreadsheets (`TECHBLITZ_RESULTS.xlsx`) using `openpyxl`.
- **Mobile Responsive & Distraction-Free**: Seamless operation on Android, iOS, tablets, and desktops.

---

## 📋 Technology Stack

- **Backend**: Python 3.11+, Flask
- **Database**: SQLite using SQLAlchemy ORM (configured for zero-friction swap to PostgreSQL or MySQL)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (zero external UI framework overhead)
- **Excel & File Processing**: `openpyxl`
- **Real-Time Communication**: High-reliability REST polling (every 2.5s) for rock-solid stability across mobile and desktop networks.

---

## ⚡ Quick Start & Installation

### 1. Clone & Navigate
```bash
cd "jits coding club"
```

### 2. Set Up Virtual Environment
```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```
The server will start on: **`http://127.0.0.1:5050`**

---

## 🔑 Default Credentials & Access Endpoints

| Portal | URL | Credentials / Inputs |
|---|---|---|
| **Candidate Test Portal** | `http://127.0.0.1:5050/` | Registered Hall Ticket, Name, Team ID |
| **Admin Control Center** | `http://127.0.0.1:5050/admin/login` | Username: `admin`<br>Password: `admin123` |

### Pre-Seeded Demo Candidate Credentials:
| Hall Ticket | Name | Team ID |
|---|---|---|
| `TB001` | Rahul | `TEAM01` |
| `TB002` | Priya | `TEAM01` |
| `TB003` | Arjun | `TEAM02` |
| `TB004` | Kiran | `TEAM02` |

---

## 📁 Registration Import & Excel Format

Organizers can export candidate lists directly from Google Forms, Microsoft Forms, or college ERP systems and drag the file into **Admin → Registrations**.

### Standard Column Format Example:
| Hall Ticket Number | Name | Team ID | Email |
|---|---|---|---|
| `JITS23A0101` | Aakash Sharma | `TEAM-01` | aakash@college.edu |
| `JITS23A0102` | Bhavana Patel | `TEAM-01` | bhavana@college.edu |
| `JITS23A0103` | Chirag Sen | `TEAM-02` | chirag@college.edu |

*Note: The importer automatically recognizes synonyms such as `HT No`, `Roll Number`, `Candidate Name`, `Team`, etc. If headers cannot be detected automatically, an interactive column mapping dialog will appear.*

Sample files are ready to test in `sample_data/`:
- `sample_data/registrations_sample.xlsx`
- `sample_data/registrations_alternate_headers.xlsx`
- `sample_data/registrations_with_duplicates.xlsx`
- `sample_data/registrations_sample.csv`

---

## 🛡️ Proctoring & Warning Protocol

```
Candidate in Exam
       ↓
Browser Violation Detected (Tab Switch, Window Blur, Fullscreen Exit, Copy/Paste)
       ↓
Server logs violation & initiates 20-Second Countdown
       ↓
Modal Warning appears on Candidate Screen (Interaction Locked)
      / \
    OK   20s Timeout
    │          │
    │     AUTOMATIC BLOCK
    │          │
    │     Candidate moves to WAITING screen
    │     Admin alerted in Live Dashboard
    │          │
    │     Admin clicks [GRANT PERMISSION] or [UNBLOCK]
    │          │
    └── Candidate Resumes Exam (Answers, Timer & Question state preserved)
```

---

## ⚠️ Browser Limitations Disclosure

> **TECHBLITZ provides browser-level assessment monitoring.** It can detect events such as tab visibility changes, window focus changes, fullscreen exits, and copy/paste attempts where supported by the browser. A normal browser cannot guarantee detection of a second physical device or every multi-monitor configuration. Therefore, the system should be described as **browser-monitored** rather than as a guaranteed anti-cheating system.

---

## 🧪 Running Automated Tests

Run the complete test suite:
```bash
PYTHONPATH=. ./venv/bin/pytest tests/test_platform.py -v
```

Run live HTTP end-to-end integration test:
```bash
./venv/bin/python tests/verify_live_api.py
```

---

## 📦 Production Deployment

To run in production behind Nginx with Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5050 app:app
```

For Render deployment:
1. Create a Render Web Service from this GitHub repository.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn --workers 4 --bind 0.0.0.0:$PORT app:app`
4. Create a Render PostgreSQL database and set `DATABASE_URL` to its connection string.
5. Set `SECRET_KEY`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD` as Render environment variables.

The registration importer accepts `.xlsx` and `.csv`. For a Google Sheet, download it first with **File → Download → Microsoft Excel (.xlsx)** or **Comma-separated values (.csv)**, then upload that downloaded file.

To switch to PostgreSQL locally:
```bash
export DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/techblitz"
python app.py
```
