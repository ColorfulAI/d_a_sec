import shlex
import sqlite3
import subprocess
from markupsafe import escape
from flask import Flask, request, redirect, jsonify

app = Flask(__name__)

ALLOWED_REDIRECTS = {
    "home": "/",
    "dashboard": "/dashboard",
    "settings": "/settings",
}

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
        return jsonify({"error": "Command not allowed"}), 400
    output = subprocess.check_output(args, shell=False)
    return jsonify({"output": output.decode()})

@app.route("/redirect")
def open_redirect():
    target = request.args.get("url", "home")
    url = ALLOWED_REDIRECTS.get(target, "/")
    return redirect(url)

@app.route("/page")
def render_page():
    title = request.args.get("title", "Home")
    content = request.args.get("content", "Welcome")
    return f"<html><head><title>{escape(title)}</title></head><body>{escape(content)}</body></html>"

if __name__ == "__main__":
    app.run()
