import sqlite3
import shlex
import subprocess
import json
import base64

from flask import Flask, request, redirect, jsonify
from markupsafe import escape

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect("app.db")
    return conn

@app.route("/search")
def search():
    query = request.args.get("q", "")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (query,))
    results = cursor.fetchall()
    return jsonify({"results": results})

ALLOWED_COMMANDS = {"echo", "date", "whoami", "uname", "hostname"}

@app.route("/run")
def run_command():
    cmd = request.args.get("cmd", "echo hello")
    args = shlex.split(cmd)
    if not args or args[0] not in ALLOWED_COMMANDS:
        return jsonify({"error": "command not allowed"}), 403
    output = subprocess.check_output(args, shell=False)
    return jsonify({"output": output.decode()})

REDIRECT_MAP = {
    "/": "/",
    "/home": "/home",
    "/dashboard": "/dashboard",
    "/profile": "/profile",
    "/search": "/search",
    "/page": "/page",
}

@app.route("/redirect")
def open_redirect():
    url = request.args.get("url", "/")
    safe_url = REDIRECT_MAP.get(url, "/")
    return redirect(safe_url)

@app.route("/profile")
def profile():
    data = request.cookies.get("session_data", "")
    if data:
        user = json.loads(base64.b64decode(data))
        return jsonify({"username": user.get("name", "anonymous")})
    return jsonify({"username": "anonymous"})

@app.route("/page")
def render_page():
    title = request.args.get("title", "Home")
    content = request.args.get("content", "")
    return f"<html><head><title>{escape(title)}</title></head><body>{escape(content)}</body></html>"

if __name__ == "__main__":
    app.run(debug=False)
