"""Stress test module 25 — intentional vulnerabilities for CodeQL testing."""
import ast
import json
import sqlite3
import os
import re
import subprocess
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR_25 = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
ALLOWED_URLS_25 = {
    "status": "https://example.com/status",
    "health": "https://api.example.com/health",
}
ALLOWED_COMMANDS_25 = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}


@app.route("/query_25_0")
def query_db_25_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))


@app.route("/cmd_25_1")
def run_cmd_25_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True)
    return result.stdout


@app.route("/read_25_2")
def read_file_25_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR_25):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return escape(f.read())


@app.route("/render_25_3")
def render_page_25_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")


@app.route("/fetch_25_4")
def fetch_url_25_4():
    url_key = request.args.get("url")
    target = ALLOWED_URLS_25.get(url_key)
    if target is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(target)
    return resp.read()


@app.route("/load_25_5")
def load_data_25_5():
    data = request.get_data()
    return escape(str(json.loads(data)))


@app.route("/proc_25_6")
def process_25_6():
    cmd = request.args.get("cmd")
    command = ALLOWED_COMMANDS_25.get(cmd)
    if command is None:
        return "Command not allowed", 403
    result = subprocess.run(command, capture_output=True)
    return result.stdout


@app.route("/ping_25_7")
def check_status_25_7():
    host = request.args.get("host")
    if not re.match(r"^[a-zA-Z0-9._-]+$", host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout


@app.route("/search_25_8")
def search_25_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))


@app.route("/calc_25_9")
def calculate_25_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
