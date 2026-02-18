"""Stress test module 27 — intentional vulnerabilities for CodeQL testing."""
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

ALLOWED_BASE_DIR_27 = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
ALLOWED_URLS_27 = {
    "status": "https://example.com/status",
    "health": "https://api.example.com/health",
}
ALLOWED_COMMANDS_27 = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}


@app.route("/query_27_0")
def query_db_27_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))


@app.route("/cmd_27_1")
def run_cmd_27_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True)
    return result.stdout


@app.route("/read_27_2")
def read_file_27_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR_27):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return escape(f.read())


@app.route("/render_27_3")
def render_page_27_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")


@app.route("/fetch_27_4")
def fetch_url_27_4():
    url_key = request.args.get("url")
    target = ALLOWED_URLS_27.get(url_key)
    if target is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(target)
    return resp.read()


@app.route("/load_27_5")
def load_data_27_5():
    data = request.get_data()
    return escape(str(json.loads(data)))


@app.route("/proc_27_6")
def process_27_6():
    cmd = request.args.get("cmd")
    command = ALLOWED_COMMANDS_27.get(cmd)
    if command is None:
        return "Command not allowed", 403
    result = subprocess.run(command, capture_output=True)
    return result.stdout


@app.route("/ping_27_7")
def check_status_27_7():
    host = request.args.get("host")
    if not re.match(r"^[a-zA-Z0-9._-]+$", host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout


@app.route("/search_27_8")
def search_27_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))


@app.route("/calc_27_9")
def calculate_27_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
