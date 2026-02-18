"""Stress test module 4 — intentional vulnerabilities for CodeQL testing."""
import ast
import html
import json
import operator
import os
import re
import sqlite3
import subprocess
import urllib.parse
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("/var/data")
ALLOWED_HOSTS = {"api.example.com", "cdn.example.com"}

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    raise ValueError("Unsupported expression")


@app.route("/query_4_0")
def query_db_4_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_4_1")
def run_cmd_4_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", "--", filename], capture_output=True, check=False)
    return "done"

@app.route("/read_4_2")
def read_file_4_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return html.escape(f.read())

@app.route("/render_4_3")
def render_page_4_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_4_4")
def fetch_url_4_4():
    url = request.args.get("url")
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return "Host not allowed", 403
    safe_url = urllib.parse.urlunparse((
        "https",
        parsed.hostname,
        parsed.path or "/",
        "",
        parsed.query,
        "",
    ))
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_4_5")
def load_data_4_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))

CMD_ALLOWLIST = {
    "ls": ["ls"],
    "cat": ["cat"],
    "date": ["date"],
    "whoami": ["whoami"],
    "uname": ["uname"],
}

@app.route("/proc_4_6")
def process_4_6():
    cmd = request.args.get("cmd")
    if cmd not in CMD_ALLOWLIST:
        return "Command not allowed", 403
    result = subprocess.run(CMD_ALLOWLIST[cmd], capture_output=True, check=False)
    return result.stdout

@app.route("/ping_4_7")
def check_status_4_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_4_8")
def search_4_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return html.escape(str(cursor.fetchall()))

@app.route("/calc_4_9")
def calculate_4_9():
    expr = request.args.get("expr")
    try:
        tree = ast.parse(expr, mode='eval')
        result = _eval_node(tree.body)
    except (ValueError, SyntaxError):
        return "Invalid expression", 400
    return str(result)
