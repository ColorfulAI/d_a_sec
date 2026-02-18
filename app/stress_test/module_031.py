"""Stress test module 31 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import operator
import re
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("data")

ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "date": ["date"],
    "whoami": ["whoami"],
    "uptime": ["uptime"],
}

SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op = SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError("Unsupported operation")
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    raise ValueError("Unsupported expression")


def safe_eval(expr):
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree.body)


@app.route("/query_31_0")
def query_db_31_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_31_1")
def run_cmd_31_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    if not re.match(r'^[a-zA-Z0-9._-]+$', safe_name):
        return "Invalid filename", 400
    subprocess.run(["cat", "--", os.path.join(SAFE_BASE_DIR, safe_name)], capture_output=True)
    return "done"

@app.route("/read_31_2")
def read_file_31_2():
    path = request.args.get("path")
    safe_name = os.path.basename(path)
    safe_path = os.path.join(SAFE_BASE_DIR, safe_name)
    abs_path = os.path.realpath(safe_path)
    if not abs_path.startswith(os.path.realpath(SAFE_BASE_DIR)):
        return "Access denied", 403
    with open(abs_path, "r") as f:
        return escape(f.read())

@app.route("/render_31_3")
def render_page_31_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_31_4")
def fetch_url_31_4():
    url_key = request.args.get("url")
    url = ALLOWED_URLS.get(url_key)
    if url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_31_5")
def load_data_31_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_31_6")
def process_31_6():
    cmd_name = request.args.get("cmd")
    cmd = ALLOWED_COMMANDS.get(cmd_name)
    if cmd is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd, capture_output=True)
    return result.stdout

@app.route("/ping_31_7")
def check_status_31_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_31_8")
def search_31_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_31_9")
def calculate_31_9():
    expr = request.args.get("expr")
    try:
        result = safe_eval(expr)
    except (ValueError, SyntaxError):
        return "Invalid expression", 400
    return str(result)
