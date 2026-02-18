"""Stress test module 12 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import html
import ast
import re
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_READ_DIR = os.path.realpath("/var/data")
ALLOWED_URL_PREFIXES = ["https://api.example.com/", "https://cdn.example.com/"]
ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime", "df": "df", "free": "free"}


@app.route("/query_12_0")
def query_db_12_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_12_1")
def run_cmd_12_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", filename], check=False, capture_output=True)
    return "done"

@app.route("/read_12_2")
def read_file_12_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(ALLOWED_READ_DIR + os.sep):
        return "Forbidden path", 403
    with open(real_path, "r") as f:
        return html.escape(f.read())

@app.route("/render_12_3")
def render_page_12_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_12_4")
def fetch_url_12_4():
    url = request.args.get("url")
    if not any(url.startswith(prefix) for prefix in ALLOWED_URL_PREFIXES):
        return "URL not allowed", 403
    resp = subprocess.run(["curl", "-s", url], capture_output=True, check=False)
    return resp.stdout

@app.route("/load_12_5")
def load_data_12_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))

@app.route("/proc_12_6")
def process_12_6():
    cmd = request.args.get("cmd")
    if cmd not in ALLOWED_COMMANDS:
        return "Command not allowed", 403
    safe_cmd = ALLOWED_COMMANDS[cmd]
    result = subprocess.run([safe_cmd], shell=False, capture_output=True, check=False)
    return result.stdout

@app.route("/ping_12_7")
def check_status_12_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_12_8")
def search_12_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return html.escape(str(cursor.fetchall()))

@app.route("/calc_12_9")
def calculate_12_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
