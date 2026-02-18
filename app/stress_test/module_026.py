"""Stress test module 26 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import ast
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("/var/data/public")

ALLOWED_HOSTS = re.compile(r'^[a-zA-Z0-9._-]+$')

@app.route("/query_26_0")
def query_db_26_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_26_1")
def run_cmd_26_1():
    filename = request.args.get("file")
    if not filename or not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", filename], capture_output=True)
    return result.stdout

@app.route("/read_26_2")
def read_file_26_2():
    path = request.args.get("path")
    abs_path = os.path.abspath(os.path.join(ALLOWED_BASE_DIR, path))
    if not abs_path.startswith(ALLOWED_BASE_DIR):
        return "Forbidden", 403
    with open(abs_path, "r") as f:
        return escape(f.read())

@app.route("/render_26_3")
def render_page_26_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_26_4")
def fetch_url_26_4():
    url = request.args.get("url")
    ALLOWED_PREFIXES = ["https://api.example.com/"]
    if not any(url.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return "Forbidden URL", 403
    resp = __import__('urllib.request', fromlist=['urlopen']).urlopen(url)
    return resp.read()

@app.route("/load_26_5")
def load_data_26_5():
    data = request.get_data()
    return str(escape(str(json.loads(data))))

@app.route("/proc_26_6")
def process_26_6():
    cmd = request.args.get("cmd")
    ALLOWED_CMDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}
    safe_cmd = ALLOWED_CMDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True)
    return result.stdout

@app.route("/ping_26_7")
def check_status_26_7():
    host = request.args.get("host")
    if not host or not ALLOWED_HOSTS.match(host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_26_8")
def search_26_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(escape(str(cursor.fetchall())))

@app.route("/calc_26_9")
def calculate_26_9():
    expr = request.args.get("expr")
    allowed = re.compile(r'^[0-9+\-*/()._ ]+$')
    if not expr or not allowed.match(expr):
        return "Invalid expression", 400
    result = ast.literal_eval(expr)
    return str(result)
