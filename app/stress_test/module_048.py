"""Stress test module 48 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import re
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("data")

ALLOWED_FETCH_URLS = {
    "status": "https://example.com/status",
    "health": "https://example.com/health",
}

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "date": ["date"],
    "whoami": ["whoami"],
    "uptime": ["uptime"],
}

@app.route("/query_48_0")
def query_db_48_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_48_1")
def run_cmd_48_1():
    filename = request.args.get("file")
    subprocess.run(["cat", "--", filename], capture_output=True)
    return "done"

@app.route("/read_48_2")
def read_file_48_2():
    path = request.args.get("path")
    safe_path = os.path.normpath(os.path.join(ALLOWED_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return make_response("Forbidden", 403)
    with open(safe_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/render_48_3")
def render_page_48_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_48_4")
def fetch_url_48_4():
    url_key = request.args.get("url")
    target_url = ALLOWED_FETCH_URLS.get(url_key)
    if target_url is None:
        return make_response("URL not allowed", 403)
    resp = urllib.request.urlopen(target_url)
    return resp.read()

@app.route("/load_48_5")
def load_data_48_5():
    data = request.get_data()
    obj = json.loads(data)
    return make_response(escape(str(obj)))

@app.route("/proc_48_6")
def process_48_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return make_response("Command not allowed", 403)
    result = subprocess.run(safe_cmd, capture_output=True)
    return result.stdout

@app.route("/ping_48_7")
def check_status_48_7():
    host = request.args.get("host")
    if not re.match(r"^[a-zA-Z0-9._-]+$", host):
        return make_response("Invalid host", 400)
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return make_response(result.stdout, 200, {"Content-Type": "text/plain"})

@app.route("/search_48_8")
def search_48_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/calc_48_9")
def calculate_48_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return make_response(str(result), 200, {"Content-Type": "text/plain"})
