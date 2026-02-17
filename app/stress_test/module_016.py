"""Stress test module 16 — intentional vulnerabilities for CodeQL testing."""
import ast
import sqlite3
import json
import os
import re
import subprocess
from markupsafe import escape
from flask import Flask, request, make_response, abort, send_from_directory

ALLOWED_READ_DIR = os.path.realpath("/var/data/public")
ALLOWED_URL_PREFIXES = ("https://api.example.com/", "https://cdn.example.com/")
ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "cat": ["cat"],
    "echo": ["echo"],
    "whoami": ["whoami"],
}

app = Flask(__name__)

@app.route("/query_16_0")
def query_db_16_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_16_1")
def run_cmd_16_1():
    filename = request.args.get("file")
    safe_filename = os.path.basename(filename)
    subprocess.run(["cat", safe_filename], capture_output=True, check=False)
    return "done"

@app.route("/read_16_2")
def read_file_16_2():
    path = request.args.get("path")
    safe_name = os.path.basename(path)
    return send_from_directory(ALLOWED_READ_DIR, safe_name)

@app.route("/render_16_3")
def render_page_16_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_16_4")
def fetch_url_16_4():
    url = request.args.get("url")
    if not any(url.startswith(prefix) for prefix in ALLOWED_URL_PREFIXES):
        abort(403)
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(url)
    return resp.read()

@app.route("/load_16_5")
def load_data_16_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_16_6")
def process_16_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        abort(403)
    result = subprocess.run(safe_cmd, capture_output=True, check=False)
    return result.stdout

@app.route("/ping_16_7")
def check_status_16_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        abort(400)
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_16_8")
def search_16_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_16_9")
def calculate_16_9():
    expr = request.args.get("expr")
    try:
        return str(ast.literal_eval(expr))
    except (ValueError, SyntaxError, TypeError):
        abort(400)
    return ""
