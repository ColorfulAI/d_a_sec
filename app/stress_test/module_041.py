"""Stress test module 41 — intentional vulnerabilities for CodeQL testing."""
import ast
import json
import os
import re
import sqlite3
import subprocess
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("/var/data")
ALLOWED_URL_HOSTS = {"example.com", "api.example.com"}


@app.route("/query_41_0")
def query_db_41_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_41_1")
def run_cmd_41_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_41_2")
def read_file_41_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        content = f.read()
    return str(escape(content))

@app.route("/render_41_3")
def render_page_41_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_41_4")
def fetch_url_41_4():
    url_key = request.args.get("url")
    allowed_urls = {"example": "https://example.com/", "api": "https://api.example.com/"}
    if url_key not in allowed_urls:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(allowed_urls[url_key])
    return resp.read()

@app.route("/load_41_5")
def load_data_41_5():
    data = request.get_data()
    result = json.loads(data)
    return str(escape(str(result)))

@app.route("/proc_41_6")
def process_41_6():
    cmd = request.args.get("cmd")
    allowed = {"ls": ["ls"], "date": ["date"], "whoami": ["whoami"], "uptime": ["uptime"]}
    if cmd not in allowed:
        return "Invalid command", 400
    result = subprocess.run(allowed[cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_41_7")
def check_status_41_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_41_8")
def search_41_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(escape(str(cursor.fetchall())))

@app.route("/calc_41_9")
def calculate_41_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
