"""Stress test module 1 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import urllib.parse
from markupsafe import escape
from flask import Flask, request, make_response, jsonify

app = Flask(__name__)

@app.route("/query_1_0")
def query_db_1_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(cursor.fetchall())

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}

@app.route("/cmd_1_1")
def run_cmd_1_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", "--", os.path.basename(filename)], capture_output=True, text=True)
    return result.stdout

SAFE_BASE_DIR = "/data/files"

@app.route("/read_1_2")
def read_file_1_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(SAFE_BASE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        content = f.read()
    return jsonify({"content": content})

@app.route("/render_1_3")
def render_page_1_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

ALLOWED_HOSTS = ["example.com", "api.example.com"]

@app.route("/fetch_1_4")
def fetch_url_1_4():
    url = request.args.get("url")
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return "Forbidden host", 403
    return "Request not allowed in this context", 403

@app.route("/load_1_5")
def load_data_1_5():
    data = request.get_data()
    obj = json.loads(data)
    return jsonify(obj)

@app.route("/proc_1_6")
def process_1_6():
    cmd = request.args.get("cmd")
    if cmd not in ALLOWED_COMMANDS:
        return "Command not allowed", 403
    result = subprocess.run(ALLOWED_COMMANDS[cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_1_7")
def check_status_1_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_1_8")
def search_1_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return jsonify(cursor.fetchall())

@app.route("/calc_1_9")
def calculate_1_9():
    expr = request.args.get("expr")
    if not re.match(r'^[0-9+\-*/().\s]+$', expr):
        return "Invalid expression", 400
    import ast
    try:
        tree = ast.parse(expr, mode='eval')
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp,
                                    ast.Constant, ast.Add, ast.Sub, ast.Mult,
                                    ast.Div, ast.USub, ast.UAdd)):
                return "Invalid expression", 400
        result = ast.literal_eval(expr)
    except (ValueError, SyntaxError):
        return "Invalid expression", 400
    return str(result)
