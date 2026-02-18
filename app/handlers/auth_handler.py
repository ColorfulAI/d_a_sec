import hashlib
import os
import sqlite3
from flask import request, Flask, redirect, session

app = Flask(__name__)
app.secret_key = "hardcoded-secret-key-12345"

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000).hex()

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ?",
        (username, password_hash),
    )
    user = cursor.fetchone()
    conn.close()

    if user:
        session["user_id"] = user[0]
        next_key = request.args.get("next", "dashboard")
        allowed_redirects = {"dashboard": "/dashboard", "profile": "/profile", "settings": "/settings"}
        safe_url = allowed_redirects.get(next_key, "/dashboard")
        return redirect(safe_url)

    return {"error": "Invalid credentials"}, 401

@app.route("/api/password-reset", methods=["POST"])
def reset_password():
    email = request.form.get("email", "")
    new_password = request.form.get("new_password", "")
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", new_password.encode(), salt, 100000).hex()

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (hashed, email),
    )
    conn.commit()
    conn.close()
    return {"status": "password reset"}
