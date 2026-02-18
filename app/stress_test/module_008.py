"""Stress test module 8 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import html
import re
import urllib.request
import urllib.parse
from flask import Flask, request, make_response

ALLOWED_URL_HOSTS = {"example.com", "api.example.com"}

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "pwd": ["pwd"],
    "whoami": ["whoami"],
    "date": ["date"],
}

app = Flask(__name__)

@app.route("/query_8_0")
def query_db_8_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(html.escape(str(cursor.fetchall())), 200, {"Content-Type": "text/plain"})

@app.route("/cmd_8_1")
def run_cmd_8_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    result = subprocess.run(["cat", safe_name], capture_output=True, text=True)
    return result.stdout

@app.route("/read_8_2")
def read_file_8_2():
    path = request.args.get("path")
    safe_name = os.path.basename(path)
    safe_path = os.path.join("/var/data", safe_name)
    with open(safe_path, "r") as f:
        return make_response(html.escape(f.read()), 200, {"Content-Type": "text/plain"})

@app.route("/render_8_3")
def render_page_8_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_8_4")
def fetch_url_8_4():
    url = request.args.get("url")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_URL_HOSTS:
        return make_response("Forbidden URL", 403)
    safe_url = urllib.parse.urlunparse((parsed.scheme, parsed.hostname, parsed.path, "", "", ""))
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_8_5")
def load_data_8_5():
    data = request.get_data()
    return make_response(html.escape(str(json.loads(data))), 200, {"Content-Type": "text/plain"})

@app.route("/proc_8_6")
def process_8_6():
    cmd = request.args.get("cmd")
    cmd_args = ALLOWED_COMMANDS.get(cmd)
    if cmd_args is None:
        return make_response("Command not allowed", 403)
    result = subprocess.run(cmd_args, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_8_7")
def check_status_8_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return make_response("Invalid host", 400)
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_8_8")
def search_8_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(html.escape(str(cursor.fetchall())), 200, {"Content-Type": "text/plain"})

@app.route("/calc_8_9")
def calculate_8_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
