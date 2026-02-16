"""Stress test module 46 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import html
import re
import urllib.request
from flask import Flask, request, make_response

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
    if not re.match(r'^[a-zA-Z0-9._/-]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", "--", filename], capture_output=True)
    return result.stdout

@app.route("/read_46_2")
def read_file_46_2():
    path = request.args.get("path")
    allowed_files = {"readme": "readme.txt", "log": "app.log", "config": "config.txt"}
    safe_name = allowed_files.get(path)
    if safe_name is None:
        return "File not allowed", 403
    full_path = os.path.join("/var/data", safe_name)
    with open(full_path, "r") as f:
        return make_response(html.escape(f.read()))

@app.route("/render_46_3")
def render_page_46_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_46_4")
def fetch_url_46_4():
    url_key = request.args.get("url")
    allowed_urls = {
        "status": "https://example.com/status",
        "health": "https://example.com/health",
    }
    if url_key not in allowed_urls:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(allowed_urls[url_key])
    return resp.read()

@app.route("/load_46_5")
def load_data_46_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))

@app.route("/proc_46_6")
def process_46_6():
    cmd = request.args.get("cmd")
    allowed_cmds = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"]}
    cmd_list = allowed_cmds.get(cmd)
    if cmd_list is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd_list, capture_output=True)
    return result.stdout

@app.route("/ping_46_7")
def check_status_46_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_46_8")
def search_46_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_46_9")
def calculate_46_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
