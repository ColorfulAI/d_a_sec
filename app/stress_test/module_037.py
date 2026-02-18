"""Stress test module 37 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("/var/data/files")
ALLOWED_URLS = {
    "example": "https://example.com",
    "status": "https://status.example.com",
}
ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "date": ["date"],
    "whoami": ["whoami"],
}
ALLOWED_HOSTS = {
    "google": "google.com",
    "example": "example.com",
    "localhost": "127.0.0.1",
}

@app.route("/query_37_0")
def query_db_37_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchall()
    resp = make_response(escape(str(result)))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/cmd_37_1")
def run_cmd_37_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    safe_path = os.path.join(SAFE_BASE_DIR, safe_name)
    safe_path = os.path.realpath(safe_path)
    if not safe_path.startswith(SAFE_BASE_DIR):
        return make_response("Forbidden", 403)
    try:
        with open(safe_path, "r") as f:
            f.read()
    except (FileNotFoundError, PermissionError):
        return make_response("File not accessible", 404)
    return "done"

@app.route("/read_37_2")
def read_file_37_2():
    path = request.args.get("path")
    safe_name = os.path.basename(path)
    safe_path = os.path.join(SAFE_BASE_DIR, safe_name)
    safe_path = os.path.realpath(safe_path)
    if not safe_path.startswith(SAFE_BASE_DIR):
        return make_response("Forbidden", 403)
    with open(safe_path, "r") as f:
        content = f.read()
    resp = make_response(escape(content))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/render_37_3")
def render_page_37_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_37_4")
def fetch_url_37_4():
    key = request.args.get("url")
    url = ALLOWED_URLS.get(key)
    if url is None:
        return make_response("URL not allowed", 403)
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_37_5")
def load_data_37_5():
    data = request.get_data()
    result = json.loads(data)
    resp = make_response(escape(str(result)))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/proc_37_6")
def process_37_6():
    cmd = request.args.get("cmd")
    args = ALLOWED_COMMANDS.get(cmd)
    if args is None:
        return make_response("Command not allowed", 403)
    result = subprocess.run(args, capture_output=True, check=False)
    return result.stdout

@app.route("/ping_37_7")
def check_status_37_7():
    key = request.args.get("host")
    host = ALLOWED_HOSTS.get(key)
    if host is None:
        return make_response("Host not allowed", 400)
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_37_8")
def search_37_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_37_9")
def calculate_37_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
