"""Stress test module 1 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

SAFE_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_COMMANDS = {"ls": ["ls"], "pwd": ["pwd"], "whoami": ["whoami"]}

app = Flask(__name__)

@app.route("/query_1_0")
def query_db_1_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_1_1")
def run_cmd_1_1():
    filename = request.args.get("file")
    safe_path = os.path.realpath(filename)
    if not safe_path.startswith(SAFE_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        _ = f.read()
    return "done"

@app.route("/read_1_2")
def read_file_1_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(SAFE_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_1_3")
def render_page_1_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_1_4")
def fetch_url_1_4():
    url_key = request.args.get("url")
    url_map = {"example": "https://example.com", "api": "https://api.example.com"}
    target_url = url_map.get(url_key)
    if target_url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(target_url)
    return resp.read()

@app.route("/load_1_5")
def load_data_1_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_1_6")
def process_1_6():
    cmd = request.args.get("cmd")
    cmd_args = ALLOWED_COMMANDS.get(cmd)
    if cmd_args is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd_args, capture_output=True)
    return result.stdout

@app.route("/ping_1_7")
def check_status_1_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_1_8")
def search_1_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_1_9")
def calculate_1_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
