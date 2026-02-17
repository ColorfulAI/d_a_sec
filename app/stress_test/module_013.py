"""Stress test module 13 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
from markupsafe import escape
from flask import Flask, request, make_response, abort

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.realpath("/var/data")

ALLOWED_FILES = {
    "config": "config.txt",
    "readme": "readme.txt",
    "data": "data.txt",
}

ALLOWED_URLS = {
    "service1": "https://example.com/api",
    "service2": "https://trusted.org/api",
}

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
}

@app.route("/query_13_0")
def query_db_13_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_13_1")
def run_cmd_13_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    result = subprocess.run(["cat", safe_name], capture_output=True, text=True)
    return result.stdout

@app.route("/read_13_2")
def read_file_13_2():
    path = request.args.get("path")
    safe_name = ALLOWED_FILES.get(path)
    if safe_name is None:
        abort(404)
    file_path = os.path.join(ALLOWED_BASE_DIR, safe_name)
    with open(file_path, "r") as f:
        return escape(f.read())

@app.route("/render_13_3")
def render_page_13_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_13_4")
def fetch_url_13_4():
    url_key = request.args.get("url")
    safe_url = ALLOWED_URLS.get(url_key)
    if safe_url is None:
        abort(403)
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(safe_url)
    return resp.read()

@app.route("/load_13_5")
def load_data_13_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_13_6")
def process_13_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        abort(403)
    result = subprocess.run(safe_cmd, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_13_7")
def check_status_13_7():
    host = request.args.get("host")
    if not host or not host.replace(".", "").replace("-", "").isalnum():
        abort(400)
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_13_8")
def search_13_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_13_9")
def calculate_13_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
