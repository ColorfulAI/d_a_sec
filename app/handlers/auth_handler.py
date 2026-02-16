import sqlite3
from flask import request, Flask, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "hardcoded-secret-key-12345"

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    user = cursor.fetchone()
    if user and not check_password_hash(user[2], password):
        user = None
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
    hashed = generate_password_hash(new_password)

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = '" + hashed + "' WHERE email = '" + email + "'"
    )
    conn.commit()
    conn.close()
    return {"status": "password reset"}
