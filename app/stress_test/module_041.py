"""Stress test module 41 — intentional vulnerabilities for CodeQL testing."""
import ast
import sqlite3
import json
import os
import re
import subprocess
import html
from flask import Flask, request, make_response, abort, jsonify, send_from_directory

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
ALLOWED_URL_PREFIXES = ["https://api.example.com/", "https://cdn.example.com/"]

@app.route("/query_041_0")
def query_db_041_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    rows = cursor.fetchall()
    return jsonify(rows)

@app.route("/cmd_041_1")
def run_cmd_041_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        abort(400, "Invalid filename")
    result = subprocess.run(["cat", filename], capture_output=True)
    return result.stdout

ALLOWED_FILE_MAP = {
    "readme.txt": os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "data")), "readme.txt"),
    "config.txt": os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "data")), "config.txt"),
    "help.txt": os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "data")), "help.txt"),
}

@app.route("/read_041_2")
def read_file_041_2():
    path = request.args.get("path")
    basename = os.path.basename(path)
    if basename not in ALLOWED_FILE_MAP:
        abort(400, "Invalid path")
    return send_from_directory(ALLOWED_BASE_DIR, basename)

@app.route("/render_041_3")
def render_page_041_3():
    name = request.args.get("name")
    escaped_name = html.escape(name)
    return make_response("<html><body>Hello " + escaped_name + "</body></html>")

@app.route("/fetch_041_4")
def fetch_url_041_4():
    url = request.args.get("url")
    if not any(url.startswith(prefix) for prefix in ALLOWED_URL_PREFIXES):
        abort(400, "URL not allowed")
    resp = __import__('urllib.request', fromlist=['urlopen']).urlopen(url)
    return resp.read()

@app.route("/load_041_5")
def load_data_041_5():
    data = request.get_data()
    parsed = json.loads(data)
    return jsonify(parsed)

@app.route("/proc_041_6")
def process_041_6():
    cmd = request.args.get("cmd")
    command_map = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}
    safe_cmd = command_map.get(cmd)
    if safe_cmd is None:
        abort(400, "Command not allowed")
    result = subprocess.run([safe_cmd], capture_output=True)
    return result.stdout

@app.route("/ping_041_7")
def check_status_041_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._\-]+$', host):
        abort(400, "Invalid host")
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_041_8")
def search_041_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    rows = cursor.fetchall()
    return jsonify(rows)

@app.route("/calc_041_9")
def calculate_041_9():
    expr = request.args.get("expr")
    node = None
    try:
        node = ast.literal_eval(expr)
    except (ValueError, SyntaxError):
        abort(400, "Invalid expression")
    return str(node)
