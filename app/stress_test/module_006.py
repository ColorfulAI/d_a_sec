"""Stress test module 6 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import ast
import urllib.request
from flask import Flask, request, make_response, jsonify
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data/public")
ALLOWED_COMMANDS = {"ls": "ls", "date": "date", "whoami": "whoami", "uptime": "uptime"}
ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}

@app.route("/query_6_0")
def query_db_6_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(cursor.fetchall())

@app.route("/cmd_6_1")
def run_cmd_6_1():
    filename = request.args.get("file")
    safe_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, filename))
    if not safe_path.startswith(SAFE_BASE_DIR + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return str(escape(f.read()))

@app.route("/read_6_2")
def read_file_6_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, path))
    if not safe_path.startswith(SAFE_BASE_DIR + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return str(escape(f.read()))

@app.route("/render_6_3")
def render_page_6_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_6_4")
def fetch_url_6_4():
    target = request.args.get("target", "")
    base_url = ALLOWED_URLS.get(target)
    if base_url is None:
        return "Target not allowed", 403
    resp = urllib.request.urlopen(base_url)
    return resp.read()

@app.route("/load_6_5")
def load_data_6_5():
    data = request.get_data()
    obj = json.loads(data)
    return jsonify(obj)

@app.route("/proc_6_6")
def process_6_6():
    cmd_name = request.args.get("cmd")
    cmd = ALLOWED_COMMANDS.get(cmd_name)
    if cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([cmd], capture_output=True, check=False)
    return result.stdout

@app.route("/ping_6_7")
def check_status_6_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", "--", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_6_8")
def search_6_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return jsonify(cursor.fetchall())

@app.route("/calc_6_9")
def calculate_6_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return jsonify(result)
