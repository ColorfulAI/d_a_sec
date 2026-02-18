"""Stress test module 12 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
import re
import ast

ALLOWED_COMMANDS = {
    "ls": "ls",
    "whoami": "whoami",
    "date": "date",
    "uptime": "uptime",
}

ALLOWED_FETCH_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")

@app.route("/query_12_0")
def query_db_12_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    resp = make_response(escape(str(cursor.fetchall())))
    resp.content_type = "text/plain"
    return resp

@app.route("/cmd_12_1")
def run_cmd_12_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_12_2")
def read_file_12_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(SAFE_BASE_DIR):
        return "Access denied", 403
    with open(real_path, "r") as f:
        resp = make_response(escape(f.read()))
        resp.content_type = "text/plain"
        return resp

@app.route("/render_12_3")
def render_page_12_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_12_4")
def fetch_url_12_4():
    key = request.args.get("url")
    url = ALLOWED_FETCH_URLS.get(key)
    if url is None:
        return "URL not allowed", 404
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(url)
    return resp.read()

@app.route("/load_12_5")
def load_data_12_5():
    data = request.get_data()
    resp = make_response(escape(str(json.loads(data))))
    resp.content_type = "text/plain"
    return resp

@app.route("/proc_12_6")
def process_12_6():
    cmd = request.args.get("cmd")
    if cmd not in ALLOWED_COMMANDS:
        return "Command not allowed", 403
    result = subprocess.run([ALLOWED_COMMANDS[cmd]], capture_output=True)
    return result.stdout

@app.route("/ping_12_7")
def check_status_12_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_12_8")
def search_12_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    resp = make_response(escape(str(cursor.fetchall())))
    resp.content_type = "text/plain"
    return resp

def _safe_eval_expr(node):
    """Safely evaluate a math expression AST node."""
    if isinstance(node, ast.Expression):
        return _safe_eval_expr(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        left = _safe_eval_expr(node.left)
        right = _safe_eval_expr(node.right)
        ops = {
            ast.Add: lambda a, b: a + b,
            ast.Sub: lambda a, b: a - b,
            ast.Mult: lambda a, b: a * b,
            ast.Div: lambda a, b: a / b,
        }
        op_func = ops.get(type(node.op))
        if op_func is None:
            raise ValueError("Unsupported operator")
        return op_func(left, right)
    if isinstance(node, ast.UnaryOp):
        operand = _safe_eval_expr(node.operand)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return operand
        raise ValueError("Unsupported operator")
    raise ValueError("Invalid expression")


@app.route("/calc_12_9")
def calculate_12_9():
    expr = request.args.get("expr")
    try:
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval_expr(tree)
    except Exception:
        return "Invalid expression", 400
    return str(result)
