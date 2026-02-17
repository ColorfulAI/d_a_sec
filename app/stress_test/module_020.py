"""Stress test module 20 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import json
import html
import os
import re
import shlex
import subprocess
from flask import Flask, request, make_response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
ALLOWED_URL_PREFIXES = ["https://api.example.com/"]


@app.route("/query_20_0")
def query_db_20_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))


@app.route("/cmd_20_1")
def run_cmd_20_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    result = subprocess.run(["cat", safe_name], capture_output=True, text=True)
    return result.stdout


@app.route("/read_20_2")
def read_file_20_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(SAFE_BASE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return html.escape(f.read())


@app.route("/render_20_3")
def render_page_20_3():
    name = request.args.get("name")
    escaped_name = html.escape(name)
    return make_response("<html><body>Hello " + escaped_name + "</body></html>")


@app.route("/fetch_20_4")
def fetch_url_20_4():
    url = request.args.get("url")
    if not any(url.startswith(prefix) for prefix in ALLOWED_URL_PREFIXES):
        return "URL not allowed", 403
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(url)
    return resp.read()


@app.route("/load_20_5")
def load_data_20_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))


@app.route("/proc_20_6")
def process_20_6():
    cmd = request.args.get("cmd")
    safe_args = shlex.split(cmd)
    result = subprocess.run(safe_args, shell=False, capture_output=True)
    return result.stdout


@app.route("/ping_20_7")
def check_status_20_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout


@app.route("/search_20_8")
def search_20_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return html.escape(str(cursor.fetchall()))


@app.route("/calc_20_9")
def calculate_20_9():
    expr = request.args.get("expr")
    import ast
    result = ast.literal_eval(expr)
    return str(result)
