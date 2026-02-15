import sqlite3
import subprocess
import json
import base64
from markupsafe import escape
from flask import Flask, request, redirect, make_response, jsonify

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
    ALLOWED_COMMANDS = {
        "echo hello": ["echo", "hello"],
        "ls": ["ls"],
        "whoami": ["whoami"],
        "date": ["date"],
    }
    cmd = request.args.get("cmd", "echo hello")
    if cmd not in ALLOWED_COMMANDS:
        return {"error": "command not allowed"}, 403
    safe_cmd = ALLOWED_COMMANDS[cmd]
    output = subprocess.check_output(safe_cmd)
    return {"output": output.decode()}

ALLOWED_REDIRECTS = {
    "/": "/",
    "/search": "/search",
    "/profile": "/profile",
    "/page": "/page",
    "/run": "/run",
}

@app.route("/redirect")
def safe_redirect():
    url = request.args.get("url", "/")
    target = ALLOWED_REDIRECTS.get(url, "/")
    return redirect(target)

@app.route("/profile")
def profile():
    data = request.cookies.get("session_data", "")
    if data:
        user = json.loads(base64.b64decode(data))
        return {"username": str(escape(user.get("name", "anonymous")))}
    return {"username": "anonymous"}

@app.route("/page")
def render_page():
    title = request.args.get("title", "Home")
    content = request.args.get("content", "")
    html = f"<html><head><title>{escape(title)}</title></head><body>{escape(content)}</body></html>"
    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html"
    return resp

if __name__ == "__main__":
    app.run(debug=False)
