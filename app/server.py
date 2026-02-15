import sqlite3
import shlex
import subprocess
import pickle
import base64
from flask import Flask, request, redirect

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

@app.route("/run")
def run_command():
    cmd = request.args.get("cmd", "echo hello")
    output = subprocess.check_output(shlex.split(cmd))
    return {"output": output.decode()}

@app.route("/redirect")
def open_redirect():
    url = request.args.get("url", "/")
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
