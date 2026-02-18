"""Stress test module 43 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
import re
import ast
from flask import Flask, request, make_response, jsonify
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}

@app.route("/query_43_0")
def query_db_43_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(cursor.fetchall())

@app.route("/cmd_43_1")
def run_cmd_43_1():
    filename = request.args.get("file")
    safe_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, filename))
    if not safe_path.startswith(SAFE_BASE_DIR + os.sep):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        f.read()
    return "done"

@app.route("/read_43_2")
def read_file_43_2():
    path = request.args.get("path")
    abs_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, path))
    if not abs_path.startswith(SAFE_BASE_DIR + os.sep):
        return "Forbidden", 403
    with open(abs_path, "r") as f:
        content = f.read()
    return jsonify({"content": content})

@app.route("/render_43_3")
def render_page_43_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_43_4")
def fetch_url_43_4():
    service = request.args.get("url")
    URL_MAP = {
        "example": "https://example.com",
        "api": "https://api.example.com",
    }
    target = URL_MAP.get(service)
    if target is None:
        return "Unknown service", 400
    resp = urllib.request.urlopen(target)
    return resp.read()

@app.route("/load_43_5")
def load_data_43_5():
    data = request.get_data()
    return jsonify(json.loads(data))

@app.route("/proc_43_6")
def process_43_6():
    cmd_input = request.args.get("cmd")
    cmd = ALLOWED_COMMANDS.get(cmd_input)
    if cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_43_7")
def check_status_43_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_43_8")
def search_43_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return jsonify(cursor.fetchall())

@app.route("/calc_43_9")
def calculate_43_9():
    expr = request.args.get("expr")
    if not re.match(r'^[0-9+\-*/().\s]+$', expr):
        return "Invalid expression", 400
    result = ast.literal_eval(expr)
    return str(result)
