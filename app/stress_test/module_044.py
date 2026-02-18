"""Stress test module 44 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_44_0")
def query_db_44_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_44_1")
def run_cmd_44_1():
    filename = request.args.get("file")
    ALLOWED_FILES = {"readme": "README.md", "log": "app.log", "config": "config.txt"}
    safe_file = ALLOWED_FILES.get(filename)
    if safe_file is None:
        return make_response("Invalid file", 400)
    subprocess.run(["cat", safe_file], check=False)
    return "done"

@app.route("/read_44_2")
def read_file_44_2():
    path = request.args.get("path")
    ALLOWED_PATHS = {"readme": "/safe_directory/README.md", "config": "/safe_directory/config.txt"}
    safe_path = ALLOWED_PATHS.get(path)
    if safe_path is None:
        return make_response("Invalid path", 400)
    with open(safe_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/render_44_3")
def render_page_44_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_44_4")
def fetch_url_44_4():
    resource = request.args.get("url")
    ALLOWED_URLS = {"status": "https://example.com/status", "health": "https://example.com/health"}
    url = ALLOWED_URLS.get(resource)
    if url is None:
        return make_response("Invalid resource", 400)
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_44_5")
def load_data_44_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))))

@app.route("/proc_44_6")
def process_44_6():
    cmd = request.args.get("cmd")
    ALLOWED_COMMANDS = {"ls": ["ls"], "date": ["date"], "uptime": ["uptime"]}
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return make_response("Invalid command", 400)
    result = subprocess.run(safe_cmd, capture_output=True, check=False)
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
