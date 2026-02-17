"""Stress test module 28 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from urllib.parse import urlparse
from markupsafe import escape
from flask import Flask, request, make_response

ALLOWED_BASE_DIR = os.path.abspath("data")
ALLOWED_URL_SCHEMES = {"https"}
ALLOWED_URL_HOSTS = {"example.com", "api.example.com"}
ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "example.com"}

app = Flask(__name__)

@app.route("/query_28_0")
def query_db_28_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_28_1")
def run_cmd_28_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], capture_output=True)
    return "done"

@app.route("/read_28_2")
def read_file_28_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        content = f.read()
        resp = make_response(str(escape(content)))
        resp.headers["Content-Type"] = "text/plain"
        return resp

@app.route("/render_28_3")
def render_page_28_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_28_4")
def fetch_url_28_4():
    url = request.args.get("url")
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_URL_SCHEMES or parsed.hostname not in ALLOWED_URL_HOSTS:
        return "Forbidden URL", 403
    safe_url = parsed.geturl()
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_28_5")
def load_data_28_5():
    data = request.get_data()
    return str(escape(str(json.loads(data))))

@app.route("/proc_28_6")
def process_28_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True)
    return result.stdout

@app.route("/ping_28_7")
def check_status_28_7():
    host = request.args.get("host")
    if host not in ALLOWED_HOSTS:
        return "Host not allowed", 403
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_28_8")
def search_28_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_28_9")
def calculate_28_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
