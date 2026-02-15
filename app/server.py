import shlex
import sqlite3
import subprocess
from urllib.parse import urlparse

from flask import Flask, abort, jsonify, request, redirect

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

@app.route("/run")
def run_command():
    ALLOWED_COMMANDS = {"echo", "date", "whoami", "uname"}
    cmd = request.args.get("cmd", "echo hello")
    args = shlex.split(cmd)
    if not args or args[0] not in ALLOWED_COMMANDS:
        abort(400, description="Command not allowed")
    output = subprocess.check_output(args, shell=False)
    return jsonify({"output": output.decode()})

@app.route("/redirect")
def safe_redirect():
    url = request.args.get("url", "/")
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        abort(400, description="External redirects are not allowed")
    if not url.startswith("/") or url.startswith("//") or "\\" in url:
        abort(400, description="Only local redirects are allowed")
    safe_path = parsed.path or "/"
    if not safe_path.startswith("/"):
        safe_path = "/"
    return redirect(safe_path)

if __name__ == "__main__":
    app.run(debug=False)
