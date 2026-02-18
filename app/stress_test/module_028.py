"""Stress test module 28 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import json
import os
import re
import subprocess
from flask import Flask, request, make_response, jsonify
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("/var/data/public")

ALLOWED_HOSTS = {"google.com", "example.com", "api.internal.local"}

ALLOWED_COMMANDS = {"ls": "ls", "cat": "cat", "whoami": "whoami", "date": "date", "uptime": "uptime"}


@app.route("/query_28_0")
def query_db_28_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(cursor.fetchall())

@app.route("/cmd_28_1")
def run_cmd_28_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    result = subprocess.run(["cat", safe_name], capture_output=True, text=True)
    return result.stdout

@app.route("/read_28_2")
def read_file_28_2():
    path = request.args.get("path")
    safe_path = os.path.abspath(os.path.join(SAFE_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(SAFE_BASE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        content = f.read()
    return make_response(str(escape(content)), 200, {"Content-Type": "text/plain"})

@app.route("/render_28_3")
def render_page_28_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_28_4")
def fetch_url_28_4():
    url = request.args.get("url")
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return "Forbidden host", 403
    resp = subprocess.run(["curl", "-s", "--max-time", "5", url], capture_output=True)
    return resp.stdout

@app.route("/load_28_5")
def load_data_28_5():
    data = request.get_data()
    return jsonify(json.loads(data))

@app.route("/proc_28_6")
def process_28_6():
    cmd = request.args.get("cmd")
    if cmd not in ALLOWED_COMMANDS:
        return "Command not allowed", 403
    safe_cmd = ALLOWED_COMMANDS[cmd]
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_28_7")
def check_status_28_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_28_8")
def search_28_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return jsonify(cursor.fetchall())

@app.route("/calc_28_9")
def calculate_28_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
