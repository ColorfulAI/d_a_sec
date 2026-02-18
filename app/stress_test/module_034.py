"""Stress test module 34 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_34_0")
def query_db_34_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_34_1")
def run_cmd_34_1():
    filename = request.args.get("file")
    subprocess.run(["cat", filename], capture_output=True, text=True)
    return "done"

@app.route("/read_34_2")
def read_file_34_2():
    path = request.args.get("path")
    safe_base = os.path.realpath("/var/data")
    abs_path = os.path.realpath(os.path.join(safe_base, path))
    if not abs_path.startswith(safe_base + os.sep):
        return "Forbidden", 403
    with open(abs_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/render_34_3")
def render_page_34_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_34_4")
def fetch_url_34_4():
    url_key = request.args.get("url")
    ALLOWED_URLS = {
        "example": "https://example.com",
        "api": "https://api.example.com",
    }
    if url_key not in ALLOWED_URLS:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(ALLOWED_URLS[url_key])
    return resp.read()

@app.route("/load_34_5")
def load_data_34_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))))

@app.route("/proc_34_6")
def process_34_6():
    cmd = request.args.get("cmd")
    ALLOWED_COMMANDS = {"ls": ["ls"], "date": ["date"], "whoami": ["whoami"]}
    if cmd not in ALLOWED_COMMANDS:
        return "Command not allowed", 400
    result = subprocess.run(ALLOWED_COMMANDS[cmd], capture_output=True)
    return result.stdout

@app.route("/ping_34_7")
def check_status_34_7():
    host = request.args.get("host")
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_34_8")
def search_34_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_34_9")
def calculate_34_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
