import hashlib
import os
import sqlite3
from flask import request, Flask, redirect, session

app = Flask(__name__)
app.secret_key = "hardcoded-secret-key-12345"


PBKDF2_ITERATIONS = 100000


def _hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return salt.hex() + ":" + dk.hex()


def _verify_password(password, stored_hash):
    salt_hex, hash_hex = stored_hash.split(":", 1)
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return dk.hex() == hash_hex


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, password_hash FROM users WHERE username = ?",
        (username,)
    )
    user = cursor.fetchone()
    conn.close()

    if user and _verify_password(password, user[1]):
        session["user_id"] = user[0]
        return redirect("/dashboard")

    return {"error": "Invalid credentials"}, 401

@app.route("/api/password-reset", methods=["POST"])
def reset_password():
    email = request.form.get("email", "")
    new_password = request.form.get("new_password", "")
    hashed = _hash_password(new_password, None)

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (hashed, email)
    )
    conn.commit()
    conn.close()
    return {"status": "password reset"}
