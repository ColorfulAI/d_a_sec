"""Stress test module 0 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import ast
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

@app.route("/query_0_0")
def query_db_0_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_0_1")
def run_cmd_0_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9._\-/]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_0_2")
def read_file_0_2():
    path = request.args.get("path")
    safe_base = os.path.realpath("/var/data")
    real_path = os.path.realpath(path)
    if not real_path.startswith(safe_base):
        return "Forbidden", 403
    with open(real_path, "r") as f:
        return str(escape(f.read()))

@app.route("/render_0_3")
def render_page_0_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_0_4")
def fetch_url_0_4():
    url = request.args.get("url")
    ALLOWED_URLS = [
        "https://example.com/api/data",
        "https://api.example.com/status",
    ]
    if url not in ALLOWED_URLS:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(ALLOWED_URLS[ALLOWED_URLS.index(url)])
    return resp.read()

@app.route("/load_0_5")
def load_data_0_5():
    data = request.get_data()
    return str(escape(str(json.loads(data))))

@app.route("/proc_0_6")
def process_0_6():
    cmd = request.args.get("cmd")
    ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_0_7")
def check_status_0_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_0_8")
def search_0_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(escape(str(cursor.fetchall())))

@app.route("/calc_0_9")
def calculate_0_9():
    expr = request.args.get("expr")
    try:
        tree = ast.parse(expr, mode='eval')
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                                    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
                                    ast.USub, ast.UAdd)):
                return "Invalid expression", 400
        result = eval(compile(tree, '<expr>', 'eval'), {"__builtins__": {}}, {})
        return str(result)
    except (SyntaxError, ValueError):
        return "Invalid expression", 400
