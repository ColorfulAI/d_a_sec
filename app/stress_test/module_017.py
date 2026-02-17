"""Stress test module 17 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("/var/data")

@app.route("/query_17_0")
def query_db_17_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_17_1")
def run_cmd_17_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], check=False)
    return "done"

@app.route("/read_17_2")
def read_file_17_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(ALLOWED_BASE_DIR):
        return make_response("Forbidden", 403)
    with open(real_path, "r") as f:
        content = f.read()
    return make_response(escape(content))

@app.route("/render_17_3")
def render_page_17_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

FETCH_TARGETS = {"example": "http://example.com", "api": "http://api.example.com"}

@app.route("/fetch_17_4")
def fetch_url_17_4():
    service = request.args.get("url")
    target = FETCH_TARGETS.get(service)
    if target is None:
        return make_response("Service not found", 404)
    resp = urllib.request.urlopen(target)
    return resp.read()

@app.route("/load_17_5")
def load_data_17_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))))

ALLOWED_COMMANDS = {"ls": ["ls"], "date": ["date"], "uptime": ["uptime"]}

@app.route("/proc_17_6")
def process_17_6():
    cmd = request.args.get("cmd")
    args = ALLOWED_COMMANDS.get(cmd)
    if args is None:
        return make_response("Command not allowed", 403)
    result = subprocess.run(args, capture_output=True, check=False)
    return result.stdout

@app.route("/ping_17_7")
def check_status_17_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return make_response("Invalid host", 400)
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_17_8")
def search_17_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(cursor.fetchall())

@app.route("/calc_17_9")
def calculate_17_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
