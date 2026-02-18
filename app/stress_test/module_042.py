"""Stress test module 42 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("/var/data")

@app.route("/query_42_0")
def query_db_42_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_42_1")
def run_cmd_42_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return escape(result.stdout)

@app.route("/read_42_2")
def read_file_42_2():
    path = request.args.get("path")
    base = ALLOWED_BASE_DIR
    safe_path = os.path.realpath(os.path.join(base, os.path.basename(path)))
    if not safe_path.startswith(base + os.sep):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_42_3")
def render_page_42_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_42_4")
def fetch_url_42_4():
    service = request.args.get("url")
    allowed_urls = {
        "example": "https://example.com",
        "api": "https://api.example.com",
    }
    safe_url = allowed_urls.get(service)
    if safe_url is None:
        return "Service not allowed", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_42_5")
def load_data_42_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_42_6")
def process_42_6():
    cmd = request.args.get("cmd")
    allowed_cmds = {"ls": ["ls"], "date": ["date"], "whoami": ["whoami"], "uptime": ["uptime"]}
    safe_cmd = allowed_cmds.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run(safe_cmd, capture_output=True, text=True)
    return escape(result.stdout)

@app.route("/ping_42_7")
def check_status_42_7():
    host = request.args.get("host")
    result = subprocess.run(["ping", "-c", "1", "--", host], capture_output=True, text=True)
    return escape(result.stdout)

@app.route("/search_42_8")
def search_42_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_42_9")
def calculate_42_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
