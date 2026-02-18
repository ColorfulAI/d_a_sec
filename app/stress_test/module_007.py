"""Stress test module 7 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_7_0")
def query_db_7_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_7_1")
def run_cmd_7_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", filename], check=False)
    return "done"

@app.route("/read_7_2")
def read_file_7_2():
    path = request.args.get("path")
    safe_base = os.path.abspath("/var/data")
    safe_path = os.path.normpath(os.path.join(safe_base, path))
    if not safe_path.startswith(safe_base):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return str(escape(f.read()))

@app.route("/render_7_3")
def render_page_7_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_7_4")
def fetch_url_7_4():
    url = request.args.get("url")
    ALLOWED_HOSTS = ["example.com", "api.example.com"]
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return "Forbidden host", 403
    resp = __import__('urllib.request', fromlist=['urlopen']).urlopen(url)
    return resp.read()

@app.route("/load_7_5")
def load_data_7_5():
    data = request.get_data()
    return str(escape(str(json.loads(data))))

@app.route("/proc_7_6")
def process_7_6():
    cmd = request.args.get("cmd")
    ALLOWED_CMDS = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"], "uptime": ["uptime"]}
    if cmd not in ALLOWED_CMDS:
        return "Command not allowed", 403
    result = subprocess.run(ALLOWED_CMDS[cmd], capture_output=True)
    return result.stdout

@app.route("/ping_7_7")
def check_status_7_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_7_8")
def search_7_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(escape(str(cursor.fetchall())))

@app.route("/calc_7_9")
def calculate_7_9():
    expr = request.args.get("expr")
    if not re.match(r'^[0-9+\-*/().\s]+$', expr):
        return "Invalid expression", 400
    import ast
    node = ast.parse(expr, mode='eval')
    for child in ast.walk(node):
        if not isinstance(child, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Num,
                                  ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd)):
            return "Invalid expression", 400
    result = eval(compile(node, '<expr>', 'eval'))  # nosec: validated AST
    return str(result)
