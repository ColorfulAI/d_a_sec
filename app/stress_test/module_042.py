"""Stress test module 42 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_FILES = {
    "readme": os.path.join(os.path.abspath("data"), "readme.txt"),
    "config": os.path.join(os.path.abspath("data"), "config.txt"),
    "log": os.path.join(os.path.abspath("data"), "log.txt"),
}
ALLOWED_URLS = {
    "status": "https://api.example.com/status",
    "health": "https://api.example.com/health",
}
ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}

@app.route("/query_42_0")
def query_db_42_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_42_1")
def run_cmd_42_1():
    filename = request.args.get("file")
    subprocess.run(["cat", "--", filename], capture_output=True)
    return "done"

@app.route("/read_42_2")
def read_file_42_2():
    key = request.args.get("path")
    file_path = ALLOWED_FILES.get(key)
    if file_path is None:
        return "File not found", 404
    with open(file_path, "r") as f:
        content = f.read()
    resp = make_response(str(escape(content)))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/render_42_3")
def render_page_42_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_42_4")
def fetch_url_42_4():
    key = request.args.get("url")
    url = ALLOWED_URLS.get(key)
    if url is None:
        return "Unknown resource", 404
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_42_5")
def load_data_42_5():
    data = request.get_data()
    return str(escape(str(json.loads(data))))

@app.route("/proc_42_6")
def process_42_6():
    cmd_key = request.args.get("cmd")
    cmd_args = ALLOWED_COMMANDS.get(cmd_key)
    if cmd_args is None:
        return "Command not allowed", 400
    result = subprocess.run(cmd_args, capture_output=True)
    return result.stdout

@app.route("/ping_42_7")
def check_status_42_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_42_8")
def search_42_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_42_9")
def calculate_42_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
