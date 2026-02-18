"""Stress test module 20 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import re
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("/var/data")

ALLOWED_URLS = {
    "example": "https://example.com/api",
    "status": "https://api.example.com/status",
}

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
}

@app.route("/query_20_0")
def query_db_20_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_20_1")
def run_cmd_20_1():
    filename = request.args.get("file")
    safe_filename = os.path.basename(filename)
    result = subprocess.run(["cat", "--", safe_filename], capture_output=True, check=False)
    return result.stdout.decode()

@app.route("/read_20_2")
def read_file_20_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_20_3")
def render_page_20_3():
    name = request.args.get("name")
    safe_name = escape(name)
    return make_response("<html><body>Hello " + safe_name + "</body></html>")

@app.route("/fetch_20_4")
def fetch_url_20_4():
    key = request.args.get("url")
    if key not in ALLOWED_URLS:
        return "URL not allowed", 403
    safe_url = ALLOWED_URLS[key]
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_20_5")
def load_data_20_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_20_6")
def process_20_6():
    cmd = request.args.get("cmd")
    if cmd not in ALLOWED_COMMANDS:
        return "Command not allowed", 403
    result = subprocess.run(ALLOWED_COMMANDS[cmd], capture_output=True, check=False)
    return result.stdout

@app.route("/ping_20_7")
def check_status_20_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_20_8")
def search_20_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_20_9")
def calculate_20_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
