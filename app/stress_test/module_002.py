"""Stress test module 2 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_FILE_DIR = os.path.realpath("/var/data/files")

ALLOWED_FETCH_URLS = {
    "status": "http://localhost/status",
    "health": "http://localhost/health",
}

ALLOWED_COMMANDS = {
    "ls": "ls",
    "whoami": "whoami",
    "date": "date",
    "uptime": "uptime",
}

ALLOWED_PING_HOSTS = {
    "localhost": "127.0.0.1",
    "google": "google.com",
}

@app.route("/query_2_0")
def query_db_2_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())), {"Content-Type": "text/plain"})

@app.route("/cmd_2_1")
def run_cmd_2_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], check=False)
    return "done"

@app.route("/read_2_2")
def read_file_2_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(SAFE_FILE_DIR, os.path.basename(path)))
    if not safe_path.startswith(SAFE_FILE_DIR):
        return make_response("Forbidden", 403)
    with open(safe_path, "r") as f:
        return make_response(escape(f.read()), {"Content-Type": "text/plain"})

@app.route("/render_2_3")
def render_page_2_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_2_4")
def fetch_url_2_4():
    url_key = request.args.get("url")
    safe_url = ALLOWED_FETCH_URLS.get(url_key)
    if safe_url is None:
        return make_response("Forbidden", 403)
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_2_5")
def load_data_2_5():
    data = request.get_data()
    parsed = json.loads(data)
    return make_response(escape(str(parsed)), {"Content-Type": "text/plain"})

@app.route("/proc_2_6")
def process_2_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return make_response("Forbidden command", 403)
    result = subprocess.run([safe_cmd], capture_output=True, check=False)
    return result.stdout

@app.route("/ping_2_7")
def check_status_2_7():
    host = request.args.get("host")
    safe_host = ALLOWED_PING_HOSTS.get(host)
    if safe_host is None:
        return make_response("Forbidden host", 403)
    result = subprocess.run(["ping", "-c", "1", safe_host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_2_8")
def search_2_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_2_9")
def calculate_2_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
