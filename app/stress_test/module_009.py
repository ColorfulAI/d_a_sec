"""Stress test module 9 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}

ALLOWED_PING_HOSTS = {
    "localhost": "127.0.0.1",
    "google": "google.com",
    "example": "example.com",
}

ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}

SAFE_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "public"))

ALLOWED_FILES = {
    "readme": "readme.txt",
    "config": "config.json",
    "log": "app.log",
}


@app.route("/query_9_0")
def query_db_9_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_9_1")
def run_cmd_9_1():
    filename = request.args.get("file")
    safe_name = ALLOWED_FILES.get(filename)
    if safe_name is None:
        return "File not allowed", 403
    safe_path = os.path.join(SAFE_BASE_DIR, safe_name)
    with open(safe_path, "r") as f:
        f.read()
    return "done"

@app.route("/read_9_2")
def read_file_9_2():
    path = request.args.get("path")
    safe_name = ALLOWED_FILES.get(path)
    if safe_name is None:
        return "File not allowed", 403
    safe_path = os.path.join(SAFE_BASE_DIR, safe_name)
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_9_3")
def render_page_9_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_9_4")
def fetch_url_9_4():
    url_key = request.args.get("url")
    target = ALLOWED_URLS.get(url_key)
    if target is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(target)
    return resp.read()

@app.route("/load_9_5")
def load_data_9_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_9_6")
def process_9_6():
    cmd = request.args.get("cmd")
    parts = ALLOWED_COMMANDS.get(cmd)
    if parts is None:
        return "Command not allowed", 403
    result = subprocess.run(parts, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_9_7")
def check_status_9_7():
    host_key = request.args.get("host")
    host = ALLOWED_PING_HOSTS.get(host_key)
    if host is None:
        return "Host not allowed", 403
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_9_8")
def search_9_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_9_9")
def calculate_9_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
