"""Stress test module 13 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import urllib.request
from html import escape as html_escape
from flask import Flask, request, make_response, jsonify

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/app/data")

@app.route("/query_13_0")
def query_db_13_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(cursor.fetchall())

@app.route("/cmd_13_1")
def run_cmd_13_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    safe_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, safe_name))
    if not safe_path.startswith(SAFE_BASE_DIR):
        return "Access denied", 403
    try:
        with open(safe_path, "r") as f:
            return make_response(html_escape(f.read()), 200, {"Content-Type": "text/plain"})
    except (FileNotFoundError, PermissionError):
        return "Error reading file", 400

@app.route("/read_13_2")
def read_file_13_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(SAFE_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return make_response(html_escape(f.read()), 200, {"Content-Type": "text/plain"})

@app.route("/render_13_3")
def render_page_13_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html_escape(name) + "</body></html>")

@app.route("/fetch_13_4")
def fetch_url_13_4():
    url_key = request.args.get("url")
    ALLOWED_URLS = {"example": "https://example.com/api", "api": "https://api.example.com/data"}
    target_url = ALLOWED_URLS.get(url_key)
    if target_url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(target_url)
    return resp.read()

@app.route("/load_13_5")
def load_data_13_5():
    data = request.get_data()
    return jsonify(json.loads(data))

@app.route("/proc_13_6")
def process_13_6():
    cmd = request.args.get("cmd")
    ALLOWED_COMMANDS = {"ls": ["ls"], "date": ["date"], "whoami": ["whoami"], "uptime": ["uptime"]}
    cmd_args = ALLOWED_COMMANDS.get(cmd)
    if cmd_args is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd_args, capture_output=True)
    return result.stdout

@app.route("/ping_13_7")
def check_status_13_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.-]*$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return make_response(result.stdout, 200, {"Content-Type": "text/plain"})

@app.route("/search_13_8")
def search_13_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return jsonify(cursor.fetchall())

@app.route("/calc_13_9")
def calculate_13_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
