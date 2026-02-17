"""Stress test module 19 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import ast
import json
import re
import urllib.request
import urllib.parse
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_19_0")
def query_db_19_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_19_1")
def run_cmd_19_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\.\-/]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", filename], capture_output=True)
    return "done"

@app.route("/read_19_2")
def read_file_19_2():
    path = request.args.get("path")
    safe_base = os.path.realpath("/var/data")
    real_path = os.path.realpath(os.path.join(safe_base, path))
    if not real_path.startswith(safe_base):
        return "Forbidden", 403
    with open(real_path, "r") as f:
        return escape(f.read())

@app.route("/render_19_3")
def render_page_19_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_19_4")
def fetch_url_19_4():
    url = request.args.get("url")
    ALLOWED_HOSTS = ["example.com", "api.example.com"]
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS or parsed.scheme not in ("http", "https"):
        return "Forbidden URL", 403
    safe_url = urllib.parse.urlunparse((parsed.scheme, parsed.hostname, parsed.path, parsed.params, parsed.query, parsed.fragment))
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_19_5")
def load_data_19_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_19_6")
def process_19_6():
    cmd = request.args.get("cmd")
    ALLOWED_CMDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}
    safe_cmd = ALLOWED_CMDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True)
    return result.stdout

@app.route("/ping_19_7")
def check_status_19_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_19_8")
def search_19_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_19_9")
def calculate_19_9():
    expr = request.args.get("expr")
    if not re.match(r'^[0-9+\-*/().\s]+$', expr):
        return "Invalid expression", 400
    result = ast.literal_eval(expr)
    return str(result)
