"""Stress test module 35 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import urllib.request
from flask import Flask, request, make_response, jsonify
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}

@app.route("/query_35_0")
def query_db_35_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(cursor.fetchall())

@app.route("/cmd_35_1")
def run_cmd_35_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_35_2")
def read_file_35_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(SAFE_BASE_DIR):
        return "Access denied", 403
    with open(real_path, "r") as f:
        resp = make_response(escape(f.read()))
        resp.headers["Content-Type"] = "text/plain"
        return resp

@app.route("/render_35_3")
def render_page_35_3():
    name = request.args.get("name")
    safe_name = str(escape(name))
    return make_response("<html><body>Hello " + safe_name + "</body></html>")

@app.route("/fetch_35_4")
def fetch_url_35_4():
    target = request.args.get("url")
    url = ALLOWED_URLS.get(target)
    if url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_35_5")
def load_data_35_5():
    data = request.get_data()
    return jsonify(json.loads(data))

@app.route("/proc_35_6")
def process_35_6():
    cmd_name = request.args.get("cmd")
    allowed_commands = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"]}
    cmd = allowed_commands.get(cmd_name)
    if cmd is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_35_7")
def check_status_35_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_35_8")
def search_35_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_35_9")
def calculate_35_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
