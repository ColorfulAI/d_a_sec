"""Stress test module 17 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import re
import html
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("/var/data")
ALLOWED_URL_PREFIXES = ("https://api.example.com/", "https://cdn.example.com/")

@app.route("/query_17_0")
def query_db_17_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_17_1")
def run_cmd_17_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_17_2")
def read_file_17_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, path))
    if not safe_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return html.escape(f.read())

@app.route("/render_17_3")
def render_page_17_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_17_4")
def fetch_url_17_4():
    url = request.args.get("url")
    if not url.startswith(ALLOWED_URL_PREFIXES):
        return "Forbidden URL", 403
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(url)
    return resp.read()

@app.route("/load_17_5")
def load_data_17_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))

ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime", "hostname": "hostname"}

@app.route("/proc_17_6")
def process_17_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Invalid command", 400
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_17_7")
def check_status_17_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_17_8")
def search_17_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return html.escape(str(cursor.fetchall()))

@app.route("/calc_17_9")
def calculate_17_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
