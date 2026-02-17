"""Stress test module 25 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "date": ["date"],
    "uptime": ["uptime"],
}
ALLOWED_PING_HOSTS = {
    "localhost": "localhost",
    "127.0.0.1": "127.0.0.1",
    "example.com": "example.com",
}
ALLOWED_URL_MAP = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}

@app.route("/query_25_0")
def query_db_25_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_25_1")
def run_cmd_25_1():
    filename = request.args.get("file")
    safe_path = os.path.realpath(filename)
    if not safe_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Access denied", 403
    result = subprocess.run(["cat", safe_path], capture_output=True, text=True)
    return result.stdout

@app.route("/read_25_2")
def read_file_25_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_25_3")
def render_page_25_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_25_4")
def fetch_url_25_4():
    target = request.args.get("url")
    safe_url = ALLOWED_URL_MAP.get(target)
    if safe_url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_25_5")
def load_data_25_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_25_6")
def process_25_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run(safe_cmd, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_25_7")
def check_status_25_7():
    host = request.args.get("host")
    safe_host = ALLOWED_PING_HOSTS.get(host)
    if safe_host is None:
        return "Host not allowed", 403
    result = subprocess.run(["ping", "-c", "1", safe_host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_25_8")
def search_25_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_25_9")
def calculate_25_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
