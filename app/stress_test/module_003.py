"""Stress test module 3 — intentional vulnerabilities for CodeQL testing."""
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

ALLOWED_READ_DIR = "/var/data"
ALLOWED_FILES = {
    "readme": "readme.txt",
    "config": "config.json",
    "log": "app.log",
}
FETCH_TARGETS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}
ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}

@app.route("/query_3_0")
def query_db_3_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_3_1")
def run_cmd_3_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_3_2")
def read_file_3_2():
    key = request.args.get("path")
    filename = ALLOWED_FILES.get(key)
    if filename is None:
        return "File not found", 404
    safe_path = os.path.join(ALLOWED_READ_DIR, filename)
    with open(safe_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/render_3_3")
def render_page_3_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_3_4")
def fetch_url_3_4():
    target = request.args.get("url")
    safe_url = FETCH_TARGETS.get(target)
    if safe_url is None:
        return "Target not allowed", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_3_5")
def load_data_3_5():
    data = request.get_data()
    parsed = json.loads(data)
    return make_response(escape(str(parsed)))

@app.route("/proc_3_6")
def process_3_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run(safe_cmd, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_3_7")
def check_status_3_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_3_8")
def search_3_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/calc_3_9")
def calculate_3_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
