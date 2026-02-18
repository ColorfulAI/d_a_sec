"""Stress test module 23 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import html
import json
import shlex
import ast
import urllib.request
from urllib.parse import urlparse
from flask import Flask, request, make_response, jsonify

app = Flask(__name__)

@app.route("/query_23_0")
def query_db_23_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(cursor.fetchall())

@app.route("/cmd_23_1")
def run_cmd_23_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", "--", filename], capture_output=True)
    return result.stdout

@app.route("/read_23_2")
def read_file_23_2():
    path = request.args.get("path")
    base_dir = os.path.realpath("data")
    safe_path = os.path.realpath(os.path.join(base_dir, path))
    if not safe_path.startswith(base_dir + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        content = html.escape(f.read())
    return make_response(content)

@app.route("/render_23_3")
def render_page_23_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_23_4")
def fetch_url_23_4():
    url = request.args.get("url")
    parsed = urlparse(url)
    if parsed.hostname == "example.com":
        safe_url = "https://example.com/"
    elif parsed.hostname == "api.example.com":
        safe_url = "https://api.example.com/"
    else:
        return "Host not allowed", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_23_5")
def load_data_23_5():
    data = request.get_data()
    return jsonify(json.loads(data))

@app.route("/proc_23_6")
def process_23_6():
    cmd = request.args.get("cmd")
    ALLOWED_CMDS = {"ls", "whoami", "date", "uptime"}
    parts = shlex.split(cmd)
    if not parts or parts[0] not in ALLOWED_CMDS:
        return "Command not allowed", 403
    result = subprocess.run(parts, capture_output=True)
    return result.stdout

@app.route("/ping_23_7")
def check_status_23_7():
    host = request.args.get("host")
    if not host or not all(c.isalnum() or c in ".-" for c in host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_23_8")
def search_23_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return jsonify(cursor.fetchall())

@app.route("/calc_23_9")
def calculate_23_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
