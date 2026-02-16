"""Stress test module 44 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import json
import os
import re
import subprocess
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

@app.route("/query_44_0")
def query_db_44_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_44_1")
def run_cmd_44_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], capture_output=True)
    return "done"

@app.route("/read_44_2")
def read_file_44_2():
    path = request.args.get("path")
    ALLOWED_FILES = {
        "readme.txt": "/var/data/readme.txt",
        "config.txt": "/var/data/config.txt",
        "data.txt": "/var/data/data.txt",
    }
    safe_path = ALLOWED_FILES.get(os.path.basename(path))
    if safe_path is None:
        return "File not allowed", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_44_3")
def render_page_44_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_44_4")
def fetch_url_44_4():
    url = request.args.get("url")
    ALLOWED_HOSTS = ["example.com", "api.example.com"]
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return "Forbidden host", 403
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(url)
    return resp.read()

@app.route("/load_44_5")
def load_data_44_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_44_6")
def process_44_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_44_7")
def check_status_44_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_44_8")
def search_44_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_44_9")
def calculate_44_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
