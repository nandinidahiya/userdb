# UserDB — Database System with User Login & Record Management

A full-stack web application built with **Python Flask + SQLite**.

---

## Quick Start

### 1. Install dependencies
```bash
pip install flask bcrypt pandas openpyxl
```

### 2. Configure email (Gmail recommended)
Open `app.py` and set these variables (or export as environment variables):
```python
EMAIL_USER     = 'your_email@gmail.com'
EMAIL_PASSWORD = 'your_gmail_app_password'   # Generate at myaccount.google.com/apppasswords
```

### 3. Run the app
```bash
python app.py
```

App runs at **http://127.0.0.1:5000**

### 4. Generate sample Excel file
```bash
python create_sample_excel.py
```
This creates `sample_data.xlsx` with 5 demo users ready to import.

---

## Workflow

### Step 1 — Bulk Import
1. Go to `/import-excel`
2. Upload `sample_data.xlsx`
3. The system reads every row, auto-generates a username & password, stores them hashed in the database, and emails credentials to each user

### Step 2 — User Login
1. User opens email, copies username & password
2. Goes to `/login`, signs in
3. On first login → redirected to `/change-password`
4. After setting a new password → lands on `/dashboard`

### Step 3 — Dashboard Actions
- **View** their full record at `/dashboard`
- **Edit** name, phone, department at `/edit`
- **Delete** their account permanently

### Step 4 — New User Registration
1. Go to `/register`, fill in name + email + phone + department
2. A 6-digit OTP is emailed
3. Enter OTP at `/verify-otp`
4. On success: credentials are generated and emailed
5. User logs in and changes password

---

## Database Schema

```sql
CREATE TABLE users (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    NOT NULL,
    email               TEXT    NOT NULL UNIQUE,
    phone               TEXT,
    department          TEXT,
    username            TEXT    NOT NULL UNIQUE,
    password_hash       TEXT    NOT NULL,         -- bcrypt hash
    must_change_password INTEGER DEFAULT 1,        -- 1 = force change on login
    is_verified         INTEGER DEFAULT 0,         -- 1 = email verified
    otp                 TEXT,                      -- pending OTP
    otp_expiry          TEXT,                      -- ISO datetime
    last_login          TEXT,
    created_at          TEXT    DEFAULT (datetime('now'))
);
```

---

## Application URLs

| URL | Description |
|-----|-------------|
| `/` | Redirects to login or dashboard |
| `/login` | User login |
| `/logout` | Clear session |
| `/change-password` | Forced on first login |
| `/dashboard` | View personal record |
| `/edit` | Edit record |
| `/delete` | Delete account (POST) |
| `/register` | New user registration |
| `/verify-otp` | OTP email verification |
| `/import-excel` | Bulk import from Excel |
| `/admin/users` | All users (admin view) |

---

## Security Features

- **bcrypt** password hashing (industry standard)
- **First-login password change** enforced
- **OTP** expires after 10 minutes
- **Session-based auth** with Flask sessions
- **Duplicate email** prevention on import and registration
- Passwords never stored in plain text anywhere

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3 + Flask |
| Database | SQLite (zero-config, swap for PostgreSQL for production) |
| Auth | bcrypt + Flask sessions |
| Email | SMTP via Gmail |
| Excel | pandas + openpyxl |
| Frontend | Jinja2 + custom CSS (no framework dependencies) |
