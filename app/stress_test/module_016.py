"""Stress test module 16 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import operator
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("/var/data/public")

ALLOWED_URLS = {
    "service1": "http://service1.internal.example.com/api",
    "service2": "http://service2.internal.example.com/api",
}

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}

ALLOWED_HOSTS = {
    "local": "127.0.0.1",
    "gateway": "192.168.1.1",
}

READABLE_FILES = {
    "readme": "readme.txt",
    "config": "config.txt",
    "status": "status.txt",
}


def _eval_node(node):
    """Safely evaluate an AST node for arithmetic expressions."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
        }
        op_fn = ops.get(type(node.op))
        if op_fn is None:
            raise ValueError("Unsupported operator")
        return op_fn(left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    raise ValueError("Invalid expression")


@app.route("/query_16_0")
def query_db_16_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))


@app.route("/cmd_16_1")
def run_cmd_16_1():
    file_key = request.args.get("file")
    filename = READABLE_FILES.get(file_key)
    if filename is None:
        return "File not found", 404
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout


@app.route("/read_16_2")
def read_file_16_2():
    path_key = request.args.get("path")
    path = READABLE_FILES.get(path_key)
    if path is None:
        return "Path not found", 404
    safe_path = os.path.join(SAFE_BASE_DIR, path)
    with open(safe_path, "r") as f:
        return make_response(escape(f.read()))


@app.route("/render_16_3")
def render_page_16_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")


@app.route("/fetch_16_4")
def fetch_url_16_4():
    service = request.args.get("url")
    url = ALLOWED_URLS.get(service)
    if url is None:
        return "Service not found", 404
    resp = urllib.request.urlopen(url)
    return resp.read()


@app.route("/load_16_5")
def load_data_16_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))))


@app.route("/proc_16_6")
def process_16_6():
    cmd_key = request.args.get("cmd")
    cmd_list = ALLOWED_COMMANDS.get(cmd_key)
    if cmd_list is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd_list, capture_output=True)
    return result.stdout


@app.route("/ping_16_7")
def check_status_16_7():
    host_key = request.args.get("host")
    host = ALLOWED_HOSTS.get(host_key)
    if host is None:
        return "Host not allowed", 403
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout


@app.route("/search_16_8")
def search_16_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(escape(str(cursor.fetchall())))


@app.route("/calc_16_9")
def calculate_16_9():
    expr = request.args.get("expr")
    try:
        tree = ast.parse(expr, mode='eval')
        result = _eval_node(tree.body)
    except (ValueError, SyntaxError, TypeError):
        return "Invalid expression", 400
    return str(result)
