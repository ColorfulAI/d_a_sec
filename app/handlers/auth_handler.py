import hashlib
import sqlite3
from flask import request, Flask, redirect, session

def _hash_password(password):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), b'app-salt-value', 100000).hex()

app = Flask(__name__)
app.secret_key = "hardcoded-secret-key-12345"

ALLOWED_REDIRECT_PATHS = {"/dashboard", "/profile", "/settings"}

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    password_hash = _hash_password(password)

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ?",
        (username, password_hash)
    )
    user = cursor.fetchone()
    conn.close()

    if user:
        session["user_id"] = user[0]
        next_key = request.args.get("next", "dashboard")
        redirect_map = {"dashboard": "/dashboard", "profile": "/profile", "settings": "/settings"}
        return redirect(redirect_map.get(next_key, "/dashboard"))

    return {"error": "Invalid credentials"}, 401

@app.route("/api/password-reset", methods=["POST"])
def reset_password():
    email = request.form.get("email", "")
    new_password = request.form.get("new_password", "")
    hashed = _hash_password(new_password)

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (hashed, email)
    )
    conn.commit()
    conn.close()
    return {"status": "password reset"}
