"""Stress test module 47 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import re
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_READ_DIR = "/var/data"
ALLOWED_COMMANDS = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"]}
ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com/data",
}

@app.route("/query_47_0")
def query_db_47_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_47_1")
def run_cmd_47_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", "--", filename], capture_output=True)
    return "done"

@app.route("/read_47_2")
def read_file_47_2():
    path = request.args.get("path")
    safe_base = os.path.realpath(SAFE_READ_DIR)
    safe_path = os.path.realpath(os.path.join(safe_base, path))
    if not safe_path.startswith(safe_base + os.sep):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        content = f.read()
    return escape(content)

@app.route("/render_47_3")
def render_page_47_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_47_4")
def fetch_url_47_4():
    key = request.args.get("url")
    url = ALLOWED_URLS.get(key)
    if url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_47_5")
def load_data_47_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_47_6")
def process_47_6():
    cmd = request.args.get("cmd")
    if cmd not in ALLOWED_COMMANDS:
        return "Command not allowed", 403
    result = subprocess.run(ALLOWED_COMMANDS[cmd], capture_output=True)
    return result.stdout

@app.route("/ping_47_7")
def check_status_47_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", "--", host], capture_output=True)
    return result.stdout.decode()

@app.route("/search_47_8")
def search_47_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_47_9")
def calculate_47_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
