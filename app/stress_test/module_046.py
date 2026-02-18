"""Stress test module 46 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import html
import re
import urllib.request
from flask import Flask, request, make_response

ALLOWED_BASE_DIR = os.path.realpath("/var/data")

app = Flask(__name__)

@app.route("/query_46_0")
def query_db_46_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_46_1")
def run_cmd_46_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        return "Invalid filename", 400
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, filename))
    if not safe_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return html.escape(f.read())

@app.route("/read_46_2")
def read_file_46_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, path))
    if not safe_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return html.escape(f.read())

@app.route("/render_46_3")
def render_page_46_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_46_4")
def fetch_url_46_4():
    service = request.args.get("url")
    url_map = {"svc1": "https://example.com/api", "svc2": "https://api.example.com/data"}
    url = url_map.get(service)
    if url is None:
        return "Unknown service", 400
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_46_5")
def load_data_46_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))

@app.route("/proc_46_6")
def process_46_6():
    cmd = request.args.get("cmd")
    cmd_map = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"], "uname": ["uname"]}
    command = cmd_map.get(cmd)
    if command is None:
        return "Command not allowed", 400
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_46_7")
def check_status_46_7():
    host = request.args.get("host")
    host_map = {"server1": "192.168.1.1", "server2": "192.168.1.2", "gateway": "192.168.1.254"}
    target = host_map.get(host)
    if target is None:
        return "Unknown host", 400
    result = subprocess.run(["ping", "-c", "1", target], capture_output=True, text=True)
    return result.stdout

@app.route("/search_46_8")
def search_46_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(cursor.fetchall())

@app.route("/calc_46_9")
def calculate_46_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
