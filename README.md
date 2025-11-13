# LinkedIn Unfollow (Selenium)

Automates unfollowing **all companies** on your LinkedIn “Interests → Companies” page.  
Logs in using credentials from a local `.env`, saves your session (cookies & Chrome profile) so future runs don’t need to log in, then scrolls and unfollows everything it finds.

> ⚠️ **Important**: Automating LinkedIn may violate LinkedIn’s Terms of Service and could result in rate limits or account restrictions. Use at your own risk and sparingly. This project is for educational purposes only.

---

## Features

- **.env login**: Reads `USERNAME` and `PASSWORD` from a local `.env` (kept out of Git).
- **Session persistence**: Reuses a dedicated Chrome profile folder and also writes a `cookies.json` backup so you typically won’t need to log in again.
- **Bulk unfollow**: Visits your Interests → Companies tab and toggles every “Following” button while scrolling until done.
- **Cross-platform**: Works on Windows, macOS, and Linux with Google Chrome.

---

## Prerequisites

- **Python** 3.10+
- **Google Chrome** installed  
  (Selenium ≥ 4.6 uses Selenium Manager to auto-fetch a matching driver)
- Terminal access (PowerShell, cmd, or bash)

---

## Quick Start

### 1) Clone & enter the repo
```bash
git clone https://github.com/<you>/<repo>.git
cd <repo>
```

### 2) Create a virtual environment & activate

**Windows – PowerShell**
```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

**Windows – Command Prompt**
```bat
python -m venv .venv
.\.venv\Scriptsctivate.bat
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies
```bash
pip install --upgrade pip
pip install selenium python-dotenv
```

### 4) Create your `.env`
```dotenv
USERNAME=your_linkedin_email@example.com
PASSWORD=your_linkedin_password_here
```

### 5) Run the script
```bash
python linkedin_unfollow.py
```

---

## Troubleshooting

**Execution policy error**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**Login or 2FA issues**: Complete 2FA manually in the browser.

**Avoid headless mode**: LinkedIn may block automation in headless browsers.

**UI Changes**: If selectors break, update the XPath logic in the script.

---

## Repository Structure

```
.
├─ linkedin_unfollow.py
├─ .gitignore
├─ README.md
```

Add to `.gitignore`:
```
cookies.json
chrome_profile/
```

---

## License

MIT

---

## Disclaimer

This tool is not affiliated with or endorsed by LinkedIn. Use responsibly.
