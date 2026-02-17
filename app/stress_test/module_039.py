"""Stress test module 39 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import html
import ast
import operator
import re
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))

ALLOWED_URLS = {
    "example": "https://example.com",
}

ALLOWED_COMMANDS = {
    "ls": "ls",
    "whoami": "whoami",
    "date": "date",
    "uptime": "uptime",
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
        op_fn = _SAFE_OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError("Unsupported operation")
        return op_fn(_safe_eval_node(node.left), _safe_eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_eval_node(node.operand)
    raise ValueError("Unsupported expression")


def safe_math_eval(expr):
    tree = ast.parse(expr, mode="eval")
    return _safe_eval_node(tree.body)


@app.route("/query_39_0")
def query_db_39_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    resp = make_response(html.escape(str(cursor.fetchall())))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/cmd_39_1")
def run_cmd_39_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    if not re.match(r'^[a-zA-Z0-9._-]+$', safe_name):
        return make_response("Invalid filename", 400)
    result = subprocess.run(["cat", safe_name], capture_output=True, text=True)
    return result.stdout

@app.route("/read_39_2")
def read_file_39_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(SAFE_BASE_DIR):
        return make_response("Forbidden", 403)
    with open(safe_path, "r") as f:
        resp = make_response(html.escape(f.read()))
        resp.headers["Content-Type"] = "text/plain"
        return resp

@app.route("/render_39_3")
def render_page_39_3():
    name = request.args.get("name")
    safe_name = html.escape(name)
    return make_response("<html><body>Hello " + safe_name + "</body></html>")

@app.route("/fetch_39_4")
def fetch_url_39_4():
    url_key = request.args.get("url")
    target = ALLOWED_URLS.get(url_key)
    if target is None:
        return make_response("URL not allowed", 403)
    resp = urllib.request.urlopen(target)
    return resp.read()

@app.route("/load_39_5")
def load_data_39_5():
    data = request.get_data()
    resp = make_response(html.escape(str(json.loads(data))))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/proc_39_6")
def process_39_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return make_response("Command not allowed", 403)
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_39_7")
def check_status_39_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return make_response("Invalid host", 400)
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_39_8")
def search_39_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    resp = make_response(html.escape(str(cursor.fetchall())))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/calc_39_9")
def calculate_39_9():
    expr = request.args.get("expr")
    try:
        result = safe_math_eval(expr)
    except Exception:
        return make_response("Invalid expression", 400)
    return str(result)
