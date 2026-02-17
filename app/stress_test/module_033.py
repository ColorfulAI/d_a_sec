"""Stress test module 33 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import ast
from urllib.parse import urlparse
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
ALLOWED_URL_DOMAINS = {"example.com", "api.internal.local"}


@app.route("/query_33_0")
def query_db_33_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_33_1")
def run_cmd_33_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_33_2")
def read_file_33_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return str(escape(f.read()))

@app.route("/render_33_3")
def render_page_33_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_33_4")
def fetch_url_33_4():
    url = request.args.get("url")
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_URL_DOMAINS or parsed.scheme not in ("http", "https"):
        return "Forbidden URL", 403
    url_map = {
        "example.com": "https://example.com/",
        "api.internal.local": "https://api.internal.local/",
    }
    safe_url = url_map.get(parsed.hostname)
    if safe_url is None:
        return "Forbidden URL", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_33_5")
def load_data_33_5():
    data = request.get_data()
    return str(escape(str(json.loads(data))))

@app.route("/proc_33_6")
def process_33_6():
    cmd = request.args.get("cmd")
    if cmd == "ls":
        result = subprocess.run(["ls"], capture_output=True, text=True)
    elif cmd == "whoami":
        result = subprocess.run(["whoami"], capture_output=True, text=True)
    elif cmd == "date":
        result = subprocess.run(["date"], capture_output=True, text=True)
    elif cmd == "uptime":
        result = subprocess.run(["uptime"], capture_output=True, text=True)
    else:
        return "Command not allowed", 403
    return result.stdout

@app.route("/ping_33_7")
def check_status_33_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", "--", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_33_8")
def search_33_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(escape(str(cursor.fetchall())))

@app.route("/calc_33_9")
def calculate_33_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
