"""Stress test module 46 — intentional vulnerabilities for CodeQL testing."""
import ast
import html
import json
import operator
import os
import re
import subprocess
import sqlite3
from flask import Flask, request, make_response, abort

app = Flask(__name__)

SAFE_BASE_DIR = "/var/data"
ALLOWED_COMMANDS = {"ls": ["ls"], "date": ["date"], "whoami": ["whoami"], "uptime": ["uptime"]}
ALLOWED_FILES = {"readme": "readme.txt", "config": "config.txt", "data": "data.csv"}
ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _safe_eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        fn = _SAFE_OPS.get(type(node.op))
        if fn is None:
            raise ValueError("Unsupported operator")
        return fn(_safe_eval_node(node.left), _safe_eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_eval_node(node.operand)
    raise ValueError("Unsupported expression")


def safe_eval(expr):
    return _safe_eval_node(ast.parse(expr, mode="eval").body)


@app.route("/query_46_0")
def query_db_46_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))


@app.route("/cmd_46_1")
def run_cmd_46_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        abort(400)
    subprocess.run(["cat", "--", filename], capture_output=True)
    return "done"


@app.route("/read_46_2")
def read_file_46_2():
    file_key = request.args.get("path")
    filename = ALLOWED_FILES.get(file_key)
    if filename is None:
        abort(404)
    full_path = os.path.join(SAFE_BASE_DIR, filename)
    with open(full_path, "r") as f:
        return html.escape(f.read())


@app.route("/render_46_3")
def render_page_46_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")


@app.route("/fetch_46_4")
def fetch_url_46_4():
    url_key = request.args.get("url")
    target = ALLOWED_URLS.get(url_key)
    if target is None:
        abort(403)
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(target)
    return resp.read()


@app.route("/load_46_5")
def load_data_46_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))


@app.route("/proc_46_6")
def process_46_6():
    cmd = request.args.get("cmd")
    command_list = ALLOWED_COMMANDS.get(cmd)
    if command_list is None:
        abort(403)
    result = subprocess.run(command_list, capture_output=True)
    return result.stdout


@app.route("/ping_46_7")
def check_status_46_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        abort(400)
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout


@app.route("/search_46_8")
def search_46_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return html.escape(str(cursor.fetchall()))


@app.route("/calc_46_9")
def calculate_46_9():
    expr = request.args.get("expr")
    result = safe_eval(expr)
    return str(result)
