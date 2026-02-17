"""Stress test module 21 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "data"))

@app.route("/query_21_0")
def query_db_21_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_21_1")
def run_cmd_21_1():
    filename = request.args.get("file")
    allowed_files = {"readme": "readme.txt", "config": "config.txt", "log": "log.txt"}
    if filename not in allowed_files:
        return "File not allowed", 403
    safe_path = os.path.join(SAFE_BASE_DIR, allowed_files[filename])
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/read_21_2")
def read_file_21_2():
    path = request.args.get("path")
    allowed_paths = {"readme": "readme.txt", "config": "config.txt", "log": "log.txt"}
    if path not in allowed_paths:
        return "Path not allowed", 403
    safe_path = os.path.join(SAFE_BASE_DIR, allowed_paths[path])
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_21_3")
def render_page_21_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_21_4")
def fetch_url_21_4():
    key = request.args.get("url")
    allowed_urls = {
        "status": "https://api.example.com/status",
        "health": "https://api.example.com/health",
    }
    if key not in allowed_urls:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(allowed_urls[key])
    return resp.read()

@app.route("/load_21_5")
def load_data_21_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_21_6")
def process_21_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_21_7")
def check_status_21_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_21_8")
def search_21_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_21_9")
def calculate_21_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
