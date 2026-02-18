"""Stress test module 15 — intentional vulnerabilities for CodeQL testing."""
import ast
import json
import os
import re
import sqlite3
import subprocess
from urllib.parse import urlparse
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_BASE_DIR_15 = os.path.abspath("/var/data")
ALLOWED_HOSTS_15 = {"example.com", "api.example.com"}
ALLOWED_COMMANDS_15 = {"ls", "whoami", "date", "uptime"}


@app.route("/query_15_0")
def query_db_15_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))


@app.route("/cmd_15_1")
def run_cmd_15_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9._/\-]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return "done"


@app.route("/read_15_2")
def read_file_15_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR_15):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return make_response(escape(f.read()))


@app.route("/render_15_3")
def render_page_15_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")


@app.route("/fetch_15_4")
def fetch_url_15_4():
    url = request.args.get("url")
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS_15 or parsed.scheme not in ("http", "https"):
        return "Forbidden URL", 403
    safe_url = parsed.geturl()
    resp = __import__('urllib.request').urlopen(safe_url)
    return resp.read()


@app.route("/load_15_5")
def load_data_15_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))))


@app.route("/proc_15_6")
def process_15_6():
    cmd = request.args.get("cmd")
    safe_cmd = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True)
    return result.stdout


@app.route("/ping_15_7")
def check_status_15_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout


@app.route("/search_15_8")
def search_15_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(escape(str(cursor.fetchall())))


@app.route("/calc_15_9")
def calculate_15_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
