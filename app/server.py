import sqlite3
import subprocess
import json
import base64
from markupsafe import escape
from flask import Flask, request, redirect, jsonify, make_response

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
    return {"results": results}

ALLOWED_COMMANDS = {
    "hello": ["echo", "hello"],
    "date": ["date"],
    "uptime": ["uptime"],
}

@app.route("/run")
def run_command():
    cmd = request.args.get("cmd", "hello")
    if cmd not in ALLOWED_COMMANDS:
        return {"error": "command not allowed"}, 400
    output = subprocess.check_output(ALLOWED_COMMANDS[cmd])
    return {"output": output.decode()}

ALLOWED_REDIRECTS = {
    "home": "/",
    "search": "/search",
    "profile": "/profile",
    "page": "/page",
}

@app.route("/redirect")
def open_redirect():
    target = request.args.get("url", "home")
    return redirect(ALLOWED_REDIRECTS.get(target, "/"))

@app.route("/profile")
def profile():
    data = request.cookies.get("session_data", "")
    if data:
        user = json.loads(base64.b64decode(data))
        return jsonify({"username": user.get("name", "anonymous")})
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
    app.run(debug=True)
