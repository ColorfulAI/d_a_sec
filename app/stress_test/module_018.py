"""Stress test module 18 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("/var/data/public")


@app.route("/query_18_0")
def query_db_18_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_18_1")
def run_cmd_18_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_18_2")
def read_file_18_2():
    path = request.args.get("path")
    safe_path = os.path.abspath(os.path.join(ALLOWED_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_18_3")
def render_page_18_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_18_4")
def fetch_url_18_4():
    url = request.args.get("url")
    ALLOWED_HOSTS = ["api.example.com", "data.example.com"]
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS or parsed.scheme not in ("http", "https"):
        return "Forbidden URL", 403
    safe_url = urlunparse((parsed.scheme, parsed.hostname, parsed.path, parsed.params, parsed.query, parsed.fragment))
    import urllib.request
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_18_5")
def load_data_18_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_18_6")
def process_18_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_18_7")
def check_status_18_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_18_8")
def search_18_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_18_9")
def calculate_18_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
