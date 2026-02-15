import sqlite3
import shlex
import subprocess
import json
import base64
from urllib.parse import urlparse
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

@app.route("/redirect")
def open_redirect():
    url = request.args.get("url", "/")
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return jsonify({"error": "external redirects not allowed"}), 400
    return redirect(url)

@app.route("/profile")
def profile():
    data = request.cookies.get("session_data", "")
    if data:
        user = pickle.loads(base64.b64decode(data))
        return {"username": user.get("name", "anonymous")}
    return {"username": "anonymous"}

@app.route("/page")
def render_page():
    title = request.args.get("title", "Home")
    content = request.args.get("content", "")
    return f"<html><head><title>{title}</title></head><body>{content}</body></html>"

if __name__ == "__main__":
    app.run(debug=True)
