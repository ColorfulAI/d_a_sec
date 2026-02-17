"""Stress test module 15 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import operator
import html
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("/var/data")

ALLOWED_HOSTS = {"127.0.0.1", "localhost"}

ALLOWED_ENDPOINTS = {
    "status": "http://localhost/status",
    "health": "http://localhost/health",
}


@app.route("/query_15_0")
def query_db_15_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_15_1")
def run_cmd_15_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    result = subprocess.run(["cat", safe_name], capture_output=True, text=True)
    return result.stdout

@app.route("/read_15_2")
def read_file_15_2():
    path = request.args.get("path")
    safe_path = os.path.join(SAFE_BASE_DIR, os.path.basename(path))
    safe_path = os.path.abspath(safe_path)
    if not safe_path.startswith(SAFE_BASE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return html.escape(f.read())

@app.route("/render_15_3")
def render_page_15_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_15_4")
def fetch_url_15_4():
    endpoint = request.args.get("url")
    safe_url = ALLOWED_ENDPOINTS.get(endpoint)
    if safe_url is None:
        return "Forbidden", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_15_5")
def load_data_15_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))

@app.route("/proc_15_6")
def process_15_6():
    cmd = request.args.get("cmd")
    allowed_commands = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}
    safe_cmd = allowed_commands.get(cmd)
    if safe_cmd is None:
        return "Forbidden", 403
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_15_7")
def check_status_15_7():
    host = request.args.get("host")
    if not host or host not in ALLOWED_HOSTS:
        return "Forbidden", 403
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_15_8")
def search_15_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return html.escape(str(cursor.fetchall()))

def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        ops = {ast.Add: operator.add, ast.Sub: operator.sub,
               ast.Mult: operator.mul, ast.Div: operator.truediv}
        if type(node.op) not in ops:
            raise ValueError("Unsupported operator")
        return ops[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_eval(node.operand)
    raise ValueError("Unsupported expression")


@app.route("/calc_15_9")
def calculate_15_9():
    expr = request.args.get("expr")
    try:
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval(tree.body)
    except (ValueError, SyntaxError):
        return "Invalid expression", 400
    return str(result)
