"""Stress test module 8 — intentional vulnerabilities for CodeQL testing."""
import ast
import operator
import sqlite3
import json
import os
import re
import subprocess
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_READ_DIR = os.path.abspath("/var/data/public")
ALLOWED_URL_PREFIXES = ("https://example.com/", "https://api.example.com/")

@app.route("/query_8_0")
def query_db_8_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_8_1")
def run_cmd_8_1():
    filename = request.args.get("file")
    if not filename or not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", "--", filename], capture_output=True, check=False)
    return "done"

@app.route("/read_8_2")
def read_file_8_2():
    path = request.args.get("path")
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(ALLOWED_READ_DIR + os.sep):
        return "Forbidden path", 403
    with open(abs_path, "r") as f:
        return escape(f.read())

@app.route("/render_8_3")
def render_page_8_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_8_4")
def fetch_url_8_4():
    url = request.args.get("url")
    if not any(url.startswith(prefix) for prefix in ALLOWED_URL_PREFIXES):
        return "URL not allowed", 403
    resp = __import__('urllib.request', fromlist=['urlopen']).urlopen(url)
    return resp.read()

@app.route("/load_8_5")
def load_data_8_5():
    data = request.get_data()
    return str(escape(str(json.loads(data))))

@app.route("/proc_8_6")
def process_8_6():
    cmd = request.args.get("cmd")
    command_map = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"], "uptime": ["uptime"]}
    safe_cmd = command_map.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run(safe_cmd, capture_output=True, check=False)
    return result.stdout

@app.route("/ping_8_7")
def check_status_8_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_8_8")
def search_8_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(escape(str(cursor.fetchall())))

@app.route("/calc_8_9")
def calculate_8_9():
    expr = request.args.get("expr")
    if not re.match(r'^[0-9+\-*/().\s]+$', expr):
        return "Invalid expression", 400
    try:
        tree = ast.parse(expr, mode='eval')
        result = _safe_eval(tree.body)
    except Exception:
        return "Invalid expression", 400
    return str(result)

_SAFE_OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
             ast.Mult: operator.mul, ast.Div: operator.truediv}

def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_eval(node.operand)
    raise ValueError("Unsupported")
