"""Stress test module 32 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import re
import json
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response, abort, jsonify

app = Flask(__name__)

@app.route("/query_32_0")
def query_db_32_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(cursor.fetchall())

@app.route("/cmd_32_1")
def run_cmd_32_1():
    filename = request.args.get("file")
    if not filename or not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        abort(400, "Invalid filename")
    safe_path = os.path.join("/var/data", filename)
    result = subprocess.run(["cat", safe_path], capture_output=True, text=True)
    return result.stdout

ALLOWED_FILES = {
    "readme": "/var/data/readme.txt",
    "config": "/var/data/config.txt",
    "data": "/var/data/data.txt",
    "status": "/var/data/status.txt",
}

@app.route("/read_32_2")
def read_file_32_2():
    path = request.args.get("path")
    file_path = ALLOWED_FILES.get(path)
    if not file_path:
        abort(400, "Invalid path")
    with open(file_path, "r") as f:
        content = f.read()
    return jsonify({"content": content})

@app.route("/render_32_3")
def render_page_32_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

ALLOWED_URL_PREFIXES = ("https://api.example.com/", "https://cdn.example.com/")

@app.route("/fetch_32_4")
def fetch_url_32_4():
    url = request.args.get("url")
    if not url or not any(url.startswith(prefix) for prefix in ALLOWED_URL_PREFIXES):
        abort(400, "URL not allowed")
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(url)
    return resp.read()

@app.route("/load_32_5")
def load_data_32_5():
    data = request.get_data()
    return jsonify(json.loads(data))

@app.route("/proc_32_6")
def process_32_6():
    cmd = request.args.get("cmd")
    allowed_commands = {"ls": "/bin/ls", "whoami": "/usr/bin/whoami", "date": "/bin/date", "uptime": "/usr/bin/uptime"}
    cmd_path = allowed_commands.get(cmd)
    if not cmd_path:
        abort(400, "Command not allowed")
    result = subprocess.run([cmd_path], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_32_7")
def check_status_32_7():
    host = request.args.get("host")
    if not host or not re.match(r'^[a-zA-Z0-9._-]+$', host):
        abort(400, "Invalid host")
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_32_8")
def search_32_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return jsonify(cursor.fetchall())

@app.route("/calc_32_9")
def calculate_32_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
