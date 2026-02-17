"""Stress test module 41 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
import urllib.parse
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_HOSTS = {"example.com", "api.example.com"}
SAFE_BASE_DIR = os.path.realpath("/var/data")

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
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_41_2")
def read_file_41_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(SAFE_BASE_DIR):
        return "Forbidden", 403
    with open(real_path, "r") as f:
        return escape(f.read())

@app.route("/render_41_3")
def render_page_41_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_41_4")
def fetch_url_41_4():
    url = request.args.get("url")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
        return "Forbidden", 403
    safe_url = urllib.parse.urlunparse(parsed)
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_41_5")
def load_data_41_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_41_6")
def process_41_6():
    cmd = request.args.get("cmd")
    allowed_cmds = {"ls": "ls", "date": "date", "whoami": "whoami", "uptime": "uptime"}
    safe_cmd = allowed_cmds.get(cmd)
    if safe_cmd is None:
        return "Forbidden", 403
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_41_7")
def check_status_41_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_41_8")
def search_41_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_41_9")
def calculate_41_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
