import sqlite3
from flask import request, Flask, redirect, session
from hashlib import pbkdf2_hmac

app = Flask(__name__)
app.secret_key = "hardcoded-secret-key-12345"

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    password_hash = pbkdf2_hmac("sha256", password.encode(), b"static-salt", 100000).hex()

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
        redirect_url = request.args.get("next", "/dashboard")
        return redirect(redirect_url)

    return {"error": "Invalid credentials"}, 401

@app.route("/api/password-reset", methods=["POST"])
def reset_password():
    email = request.form.get("email", "")
    new_password = request.form.get("new_password", "")
    hashed = pbkdf2_hmac("sha256", new_password.encode(), b"static-salt", 100000).hex()

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (hashed, email),
    )
    conn.commit()
    conn.close()
    return {"status": "password reset"}
