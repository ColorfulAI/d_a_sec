"""Stress test module 46 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import urllib.parse
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_46_0")
def query_db_46_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_46_1")
def run_cmd_46_1():
    filename = request.args.get("file")
    safe_filename = os.path.basename(filename)
    result = subprocess.run(["cat", safe_filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_46_2")
def read_file_46_2():
    path = request.args.get("path")
    ALLOWED_FILES = {
        "readme.txt": "/safe/dir/readme.txt",
        "config.txt": "/safe/dir/config.txt",
        "data.txt": "/safe/dir/data.txt",
        "help.txt": "/safe/dir/help.txt",
    }
    safe_path = ALLOWED_FILES.get(os.path.basename(path))
    if safe_path is None:
        return "File not allowed", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_46_3")
def render_page_46_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_46_4")
def fetch_url_46_4():
    url = request.args.get("url")
    ALLOWED_HOSTS = ["example.com", "api.example.com"]
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
        return "Forbidden host", 403
    safe_url = urllib.parse.urlunparse((parsed.scheme, parsed.hostname, parsed.path, "", parsed.query, ""))
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_46_5")
def load_data_46_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_46_6")
def process_46_6():
    cmd = request.args.get("cmd")
    ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date"}
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_46_7")
def check_status_46_7():
    host = request.args.get("host")
    if not re.match(r"^[a-zA-Z0-9.\-]+$", host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_46_8")
def search_46_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_46_9")
def calculate_46_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
