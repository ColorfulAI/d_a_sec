"""Stress test module 6 — intentional vulnerabilities for CodeQL testing."""
import ast
import sqlite3
import json
import os
import re
import shlex
import subprocess
from markupsafe import escape
from flask import Flask, request, make_response

ALLOWED_BASE_DIR = os.path.abspath("/var/data")
ALLOWED_HOSTS = re.compile(r"^[a-zA-Z0-9._-]+$")
ALLOWED_URL_PREFIXES = ["https://api.example.com/", "https://cdn.example.com/"]

app = Flask(__name__)

@app.route("/query_6_0")
def query_db_6_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_6_1")
def run_cmd_6_1():
    filename = request.args.get("file")
    safe_filename = shlex.quote(filename)
    subprocess.run(["cat", safe_filename], capture_output=True, check=False)
    return "done"

@app.route("/read_6_2")
def read_file_6_2():
    path = request.args.get("path")
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(ALLOWED_BASE_DIR):
        return "Forbidden", 403
    with open(abs_path, "r") as f:
        return escape(f.read())

@app.route("/render_6_3")
def render_page_6_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_6_4")
def fetch_url_6_4():
    url = request.args.get("url")
    if not any(url.startswith(prefix) for prefix in ALLOWED_URL_PREFIXES):
        return "Forbidden URL", 403
    resp = subprocess.run(["curl", "-s", url], capture_output=True, check=False)
    return resp.stdout

@app.route("/load_6_5")
def load_data_6_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_6_6")
def process_6_6():
    cmd = request.args.get("cmd")
    allowed_commands = {"ls": "/bin/ls", "whoami": "/usr/bin/whoami", "date": "/bin/date", "uptime": "/usr/bin/uptime"}
    cmd_path = allowed_commands.get(cmd)
    if cmd_path is None:
        return "Command not allowed", 403
    result = subprocess.run([cmd_path], capture_output=True, check=False)
    return result.stdout

@app.route("/ping_6_7")
def check_status_6_7():
    host = request.args.get("host")
    if not ALLOWED_HOSTS.match(host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_6_8")
def search_6_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_6_9")
def calculate_6_9():
    expr = request.args.get("expr")
    try:
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                                    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
                                    ast.USub, ast.UAdd)):
                return "Invalid expression", 400
        result = ast.literal_eval(expr)
    except (ValueError, SyntaxError):
        return "Invalid expression", 400
    return str(result)
