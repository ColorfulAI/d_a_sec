"""Stress test module 31 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import html
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("uploads")

ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}

ALLOWED_HOSTS = {
    "localhost": "127.0.0.1",
    "gateway": "192.168.1.1",
}

@app.route("/query_31_0")
def query_db_31_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_31_1")
def run_cmd_31_1():
    filename = request.args.get("file")
    base = os.path.realpath(ALLOWED_BASE_DIR)
    safe_path = os.path.realpath(os.path.join(base, filename))
    if not safe_path.startswith(base + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        f.read()
    return "done"

@app.route("/read_31_2")
def read_file_31_2():
    path = request.args.get("path")
    base = os.path.realpath(ALLOWED_BASE_DIR)
    safe_path = os.path.realpath(os.path.join(base, path))
    if not safe_path.startswith(base + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return html.escape(f.read())

@app.route("/render_31_3")
def render_page_31_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_31_4")
def fetch_url_31_4():
    url_key = request.args.get("url")
    target = ALLOWED_URLS.get(url_key)
    if target is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(target)
    return resp.read()

@app.route("/load_31_5")
def load_data_31_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))

@app.route("/proc_31_6")
def process_31_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run(safe_cmd, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_31_7")
def check_status_31_7():
    host = request.args.get("host")
    safe_host = ALLOWED_HOSTS.get(host)
    if safe_host is None:
        return "Host not allowed", 403
    result = subprocess.run(["ping", "-c", "1", safe_host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_31_8")
def search_31_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return html.escape(str(cursor.fetchall()))

@app.route("/calc_31_9")
def calculate_31_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
