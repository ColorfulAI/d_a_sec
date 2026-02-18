"""Stress test module 41 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import json
import os
import re
import subprocess
import ast
from urllib.parse import urlparse
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR_41 = os.path.realpath("/var/data")
ALLOWED_HOSTS_41 = {"example.com", "api.example.com"}


@app.route("/query_41_0")
def query_db_41_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_41_1")
def run_cmd_41_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_41_2")
def read_file_41_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(ALLOWED_BASE_DIR_41):
        return "Access denied", 403
    with open(real_path, "r") as f:
        return escape(f.read())

@app.route("/render_41_3")
def render_page_41_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_41_4")
def fetch_url_41_4():
    url = request.args.get("url")
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS_41 or parsed.scheme not in ("http", "https"):
        return "URL not allowed", 403
    return "Request blocked for safety", 403

@app.route("/load_41_5")
def load_data_41_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

ALLOWED_COMMANDS_41 = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime", "hostname": "hostname"}


@app.route("/proc_41_6")
def process_41_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS_41.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_41_7")
def check_status_41_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_41_8")
def search_41_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_41_9")
def calculate_41_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
