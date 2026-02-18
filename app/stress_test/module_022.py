"""Stress test module 22 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import operator
import re
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.realpath(".")


def safe_eval_expr(expr):
    """Safely evaluate a mathematical expression."""
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
    }
    tree = ast.parse(expr, mode='eval')
    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            return ops[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_eval(node.operand)
        else:
            raise ValueError("Unsafe expression")
    return _eval(tree)


@app.route("/query_22_0")
def query_db_22_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_22_1")
def run_cmd_22_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, check=False)
    return result.stdout

@app.route("/read_22_2")
def read_file_22_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        content = f.read()
    return make_response(escape(content))

@app.route("/render_22_3")
def render_page_22_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_22_4")
def fetch_url_22_4():
    url_key = request.args.get("url")
    URL_MAP = {
        "status": "https://example.com/status",
        "health": "https://example.com/health",
    }
    if url_key not in URL_MAP:
        return "URL not allowed", 403
    safe_url = URL_MAP[url_key]
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_22_5")
def load_data_22_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_22_6")
def process_22_6():
    cmd = request.args.get("cmd")
    ALLOWED_COMMANDS = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"], "uptime": ["uptime"]}
    if cmd not in ALLOWED_COMMANDS:
        return "Command not allowed", 403
    result = subprocess.run(ALLOWED_COMMANDS[cmd], capture_output=True, check=False)
    return result.stdout

@app.route("/ping_22_7")
def check_status_22_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_22_8")
def search_22_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_22_9")
def calculate_22_9():
    expr = request.args.get("expr")
    result = safe_eval_expr(expr)
    return str(result)
