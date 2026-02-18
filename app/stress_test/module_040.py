"""Stress test module 40 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_40_0")
def query_db_40_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_40_1")
def run_cmd_40_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", "--", filename], capture_output=True, check=False)
    return "done"

ALLOWED_BASE_DIR = os.path.abspath("/var/data/files")
ALLOWED_FILES = {
    "readme": "readme.txt",
    "config": "config.txt",
    "data": "data.csv",
}


@app.route("/read_40_2")
def read_file_40_2():
    file_key = request.args.get("path")
    filename = ALLOWED_FILES.get(file_key)
    if filename is None:
        return "Forbidden", 403
    safe_path = os.path.join(ALLOWED_BASE_DIR, filename)
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_40_3")
def render_page_40_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}


@app.route("/fetch_40_4")
def fetch_url_40_4():
    url_key = request.args.get("url")
    target_url = ALLOWED_URLS.get(url_key)
    if target_url is None:
        return "Forbidden host", 403
    resp = urllib.request.urlopen(target_url)
    return resp.read()

@app.route("/load_40_5")
def load_data_40_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}


@app.route("/proc_40_6")
def process_40_6():
    cmd = request.args.get("cmd")
    cmd_args = ALLOWED_COMMANDS.get(cmd)
    if cmd_args is None:
        return "Invalid command", 400
    result = subprocess.run(cmd_args, capture_output=True, check=False)
    return result.stdout

@app.route("/ping_40_7")
def check_status_40_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_40_8")
def search_40_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_40_9")
def calculate_40_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
