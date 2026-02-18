"""Stress test module 5 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response, abort
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_FILES = {"readme.txt": "readme.txt", "config.txt": "config.txt", "data.csv": "data.csv"}
ALLOWED_URLS = {"https://example.com": "https://example.com", "https://api.example.com": "https://api.example.com"}
ALLOWED_COMMANDS = {"ls": "ls", "date": "date", "whoami": "whoami", "uptime": "uptime"}

@app.route("/query_5_0")
def query_db_5_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_5_1")
def run_cmd_5_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, check=False)
    return result.stdout

@app.route("/read_5_2")
def read_file_5_2():
    path = request.args.get("path")
    safe_name = ALLOWED_FILES.get(path)
    if safe_name is None:
        abort(403)
    safe_path = os.path.join(SAFE_BASE_DIR, safe_name)
    with open(safe_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/render_5_3")
def render_page_5_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_5_4")
def fetch_url_5_4():
    url = request.args.get("url")
    safe_url = ALLOWED_URLS.get(url)
    if safe_url is None:
        abort(403)
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_5_5")
def load_data_5_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))))

@app.route("/proc_5_6")
def process_5_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        abort(403)
    result = subprocess.run([safe_cmd], capture_output=True, check=False)
    return result.stdout

@app.route("/ping_5_7")
def check_status_5_7():
    host = request.args.get("host")
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_5_8")
def search_5_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/calc_5_9")
def calculate_5_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
