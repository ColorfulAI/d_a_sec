"""Stress test module 32 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import subprocess
import json
import ast
import re
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

ALLOWED_URLS = {
    "example": "https://example.com",
    "status": "https://example.com/status",
}

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}

ALLOWED_FILES = {
    "readme": "/var/data/readme.txt",
    "config": "/var/data/config.txt",
}

app = Flask(__name__)

@app.route("/query_32_0")
def query_db_32_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_32_1")
def run_cmd_32_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_32_2")
def read_file_32_2():
    path_key = request.args.get("path")
    real_path = ALLOWED_FILES.get(path_key)
    if real_path is None:
        return "File not allowed", 403
    with open(real_path, "r") as f:
        return str(escape(f.read()))

@app.route("/render_32_3")
def render_page_32_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_32_4")
def fetch_url_32_4():
    url_key = request.args.get("url")
    url = ALLOWED_URLS.get(url_key)
    if url is None:
        return "URL not allowed", 400
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_32_5")
def load_data_32_5():
    data = request.get_data()
    return str(escape(str(json.loads(data))))

@app.route("/proc_32_6")
def process_32_6():
    cmd = request.args.get("cmd")
    args = ALLOWED_COMMANDS.get(cmd)
    if args is None:
        return "Command not allowed", 403
    result = subprocess.run(args, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_32_7")
def check_status_32_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_32_8")
def search_32_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(escape(str(cursor.fetchall())))

@app.route("/calc_32_9")
def calculate_32_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
