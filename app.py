"""
Database System with User Login and Record Management
Built with Flask + SQLite
Deploy: Render.com | Email: Mailtrap
"""

import os
import random
import secrets
import string
import smtplib
import sqlite3
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, g)

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'database.db')

EMAIL_HOST     = os.getenv('EMAIL_HOST',     'sandbox.smtp.mailtrap.io')
EMAIL_PORT     = int(os.getenv('EMAIL_PORT', '2525'))
EMAIL_USER     = os.getenv('EMAIL_USER',     '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
EMAIL_FROM     = os.getenv('EMAIL_FROM',     'system@userdb.com')

# ──────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                name                 TEXT    NOT NULL,
                email                TEXT    NOT NULL UNIQUE,
                phone                TEXT,
                department           TEXT,
                username             TEXT    NOT NULL UNIQUE,
                password_hash        TEXT    NOT NULL,
                must_change_password INTEGER DEFAULT 1,
                is_verified          INTEGER DEFAULT 0,
                otp                  TEXT,
                otp_expiry           TEXT,
                last_login           TEXT,
                created_at           TEXT    DEFAULT (datetime('now'))
            );
        """)
        db.commit()

# ──────────────────────────────────────────────
# UTILITIES
# ──────────────────────────────────────────────
def generate_password(length=10):
    chars = string.ascii_letters + string.digits + '!@#$'
    return ''.join(secrets.choice(chars) for _ in range(length))

def generate_username(name, db):
    parts = name.lower().split()
    base  = f"{parts[0]}.{parts[-1]}" if len(parts) > 1 else parts[0]
    base  = ''.join(c for c in base if c.isalnum() or c == '.')
    username, counter = base, 1
    while db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
        username = f"{base}{counter}"
        counter += 1
    return username

def hash_password(plain):
    return generate_password_hash(plain)

def check_password(plain, hashed):
    return check_password_hash(hashed, plain)

def send_email(to_email, subject, html_body):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        import re
        plain = re.sub('<[^>]+>', '', html_body).strip()
        print(f"\n{'='*55}\n📧  TO: {to_email}\n📌  {subject}\n{plain}\n{'='*55}\n")
        return True
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = EMAIL_FROM
        msg['To']      = to_email
        msg.attach(MIMEText(html_body, 'html'))
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"[EMAIL OK] '{subject}' → {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

def credentials_email(name, username, password, email):
    html = f"""
    <div style="font-family:Georgia,serif;max-width:560px;margin:auto;background:#0d0d0d;
                color:#e8e0d0;padding:40px;border-radius:8px;">
      <h2 style="color:#c9a96e;letter-spacing:2px;font-size:22px;">YOUR ACCESS CREDENTIALS</h2>
      <p>Hello <strong>{name}</strong>,</p>
      <p>Your account has been created. Use the details below to sign in:</p>
      <div style="background:#1a1a1a;padding:20px;border-left:3px solid #c9a96e;margin:24px 0;border-radius:4px;">
        <p style="margin:4px 0;"><span style="color:#c9a96e;">Username:</span> <strong>{username}</strong></p>
        <p style="margin:4px 0;"><span style="color:#c9a96e;">Password:</span> <strong>{password}</strong></p>
      </div>
      <p style="color:#999;font-size:13px;">You will be asked to change your password on first login.</p>
    </div>"""
    send_email(email, "Your Login Credentials", html)

def otp_email(name, otp, email):
    html = f"""
    <div style="font-family:Georgia,serif;max-width:560px;margin:auto;background:#0d0d0d;
                color:#e8e0d0;padding:40px;border-radius:8px;">
      <h2 style="color:#c9a96e;letter-spacing:2px;font-size:22px;">VERIFY YOUR EMAIL</h2>
      <p>Hello <strong>{name}</strong>,</p>
      <p>Your one-time verification code is:</p>
      <div style="background:#1a1a1a;padding:24px;text-align:center;
                  border-left:3px solid #c9a96e;margin:24px 0;border-radius:4px;">
        <span style="font-size:36px;letter-spacing:12px;color:#c9a96e;font-weight:bold;">{otp}</span>
      </div>
      <p style="color:#999;font-size:13px;">This code expires in 10 minutes.</p>
    </div>"""
    send_email(email, "Email Verification OTP", html)

# ──────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' not in session:
        return None
    return get_db().execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()

# ──────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        db   = get_db()
        user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if user and check_password(password, user['password_hash']):
            session['user_id'] = user['id']
            db.execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user['id'],))
            db.commit()
            if user['must_change_password']:
                flash('Please set a new password before continuing.', 'info')
                return redirect(url_for('change_password'))
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = get_current_user()
    if request.method == 'POST':
        current  = request.form.get('current_password', '')
        new_pass = request.form.get('new_password', '')
        confirm  = request.form.get('confirm_password', '')
        if not check_password(current, user['password_hash']):
            flash('Current password is incorrect.', 'error')
        elif len(new_pass) < 8:
            flash('New password must be at least 8 characters.', 'error')
        elif new_pass != confirm:
            flash('Passwords do not match.', 'error')
        else:
            db = get_db()
            db.execute('UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?',
                       (hash_password(new_pass), user['id']))
            db.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('change_password.html', user=user)

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    if user['must_change_password']:
        return redirect(url_for('change_password'))
    return render_template('dashboard.html', user=user)

@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    user = get_current_user()
    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        phone      = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        if not name:
            flash('Name cannot be empty.', 'error')
        else:
            db = get_db()
            db.execute('UPDATE users SET name=?, phone=?, department=? WHERE id=?',
                       (name, phone, department, user['id']))
            db.commit()
            flash('Record updated successfully!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('edit.html', user=user)

@app.route('/delete', methods=['POST'])
@login_required
def delete():
    db = get_db()
    db.execute('DELETE FROM users WHERE id=?', (session['user_id'],))
    db.commit()
    session.clear()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name       = request.form.get('name', '').strip()
        email      = request.form.get('email', '').strip().lower()
        phone      = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        if not name or not email:
            flash('Name and email are required.', 'error')
            return render_template('register.html')
        db = get_db()
        if db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
            flash('An account with this email already exists.', 'error')
            return render_template('register.html')
        otp    = str(random.randint(100000, 999999))
        expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
        session['pending_reg'] = {
            'name': name, 'email': email, 'phone': phone,
            'department': department, 'otp': otp, 'otp_expiry': expiry
        }
        otp_email(name, otp, email)
        flash(f'OTP sent to {email}. Check your inbox (and spam folder).', 'info')
        return redirect(url_for('verify_otp'))
    return render_template('register.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    pending = session.get('pending_reg')
    if not pending:
        return redirect(url_for('register'))
    if request.method == 'POST':
        entered = request.form.get('otp', '').strip()
        expiry  = datetime.fromisoformat(pending['otp_expiry'])
        if datetime.now() > expiry:
            flash('OTP expired. Please register again.', 'error')
            session.pop('pending_reg', None)
            return redirect(url_for('register'))
        if entered != pending['otp']:
            flash('Incorrect OTP. Try again.', 'error')
            return render_template('verify_otp.html', email=pending['email'])
        db       = get_db()
        username = generate_username(pending['name'], db)
        plain_pw = generate_password()
        db.execute("""
            INSERT INTO users (name, email, phone, department, username,
                               password_hash, must_change_password, is_verified)
            VALUES (?,?,?,?,?,?,1,1)
        """, (pending['name'], pending['email'], pending['phone'],
              pending['department'], username, hash_password(plain_pw)))
        db.commit()
        credentials_email(pending['name'], username, plain_pw, pending['email'])
        session.pop('pending_reg', None)
        flash('Email verified! Your login credentials have been sent to your inbox.', 'success')
        return redirect(url_for('login'))
    return render_template('verify_otp.html', email=pending['email'])

@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    pending = session.get('pending_reg')
    if not pending:
        return redirect(url_for('register'))
    otp    = str(random.randint(100000, 999999))
    expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
    pending.update({'otp': otp, 'otp_expiry': expiry})
    session['pending_reg'] = pending
    otp_email(pending['name'], otp, pending['email'])
    flash('A new OTP has been sent.', 'info')
    return redirect(url_for('verify_otp'))

@app.route('/import-excel', methods=['GET', 'POST'])
def import_excel():
    if request.method == 'POST':
        file = request.files.get('excel_file')
        if not file or not file.filename.endswith(('.xlsx', '.xls')):
            flash('Please upload a valid Excel file (.xlsx or .xls).', 'error')
            return render_template('import_excel.html')
        try:
            df = pd.read_excel(file)
            df.columns = [c.strip().lower() for c in df.columns]
            if not {'name', 'email'}.issubset(set(df.columns)):
                flash('Excel must have at least "Name" and "Email" columns.', 'error')
                return render_template('import_excel.html')
            db = get_db()
            created, skipped = 0, 0
            for _, row in df.iterrows():
                name  = str(row.get('name',  '')).strip()
                email = str(row.get('email', '')).strip().lower()
                phone = str(row.get('phone', '')).strip() if 'phone' in row else ''
                dept  = str(row.get('department', '')).strip() if 'department' in row else ''
                if not name or not email or email == 'nan':
                    skipped += 1; continue
                if db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
                    skipped += 1; continue
                username = generate_username(name, db)
                plain_pw = generate_password()
                db.execute("""
                    INSERT INTO users (name, email, phone, department, username,
                                       password_hash, must_change_password, is_verified)
                    VALUES (?,?,?,?,?,?,1,1)
                """, (name, email, phone, dept, username, hash_password(plain_pw)))
                db.commit()
                credentials_email(name, username, plain_pw, email)
                created += 1
            flash(f'Import complete — {created} users created, {skipped} skipped.', 'success')
        except Exception as e:
            flash(f'Error processing file: {e}', 'error')
        return render_template('import_excel.html')
    return render_template('import_excel.html')

@app.route('/admin/users')
def admin_users():
    db    = get_db()
    users = db.execute(
        'SELECT id,name,email,username,department,last_login,created_at '
        'FROM users ORDER BY created_at DESC'
    ).fetchall()
    return render_template('admin_users.html', users=users)

# ──────────────────────────────────────────────
# STARTUP
# ──────────────────────────────────────────────
init_db()

    with app.app_context():
        db = get_db()
        if not db.execute("SELECT id FROM users WHERE username='demo.user'").fetchone():
            db.execute("""
                INSERT INTO users (name, email, phone, department, username,
                                   password_hash, must_change_password, is_verified)
                VALUES (?,?,?,?,?,?,0,1)
            """, ('Demo User', 'demo@example.com', '+91-9999999999',
                  'Engineering', 'demo.user', hash_password('Demo@1234')))
            db.commit()
            print("👤  Demo user created → username: demo.user  |  password: Demo@1234")
if __name__ == '__main__':
    print("\n🚀  http://127.0.0.1:5000")
    print("📥  Import  → http://127.0.0.1:5000/import-excel")
    print("👑  Admin   → http://127.0.0.1:5000/admin/users\n")
    app.run(debug=True)
