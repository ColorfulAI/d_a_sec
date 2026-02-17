"""Stress test module 37 — intentional vulnerabilities for CodeQL testing."""
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

@app.route("/query_37_0")
def query_db_37_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchall()
    return make_response(escape(str(result)))

@app.route("/cmd_37_1")
def run_cmd_37_1():
    filename = request.args.get("file")
    if not filename or not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_37_2")
def read_file_37_2():
    path = request.args.get("path")
    safe_dir = os.path.realpath("/var/data")
    requested_path = os.path.realpath(os.path.join(safe_dir, path))
    if not requested_path.startswith(safe_dir + os.sep):
        return "Forbidden", 403
    with open(requested_path, "r") as f:
        content = f.read()
    return make_response(escape(content))

@app.route("/render_37_3")
def render_page_37_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_37_4")
def fetch_url_37_4():
    url_key = request.args.get("url")
    ALLOWED_URLS = {
        "example": "https://example.com",
        "api": "https://api.example.com",
    }
    target_url = ALLOWED_URLS.get(url_key)
    if not target_url:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(target_url)
    return resp.read()

@app.route("/load_37_5")
def load_data_37_5():
    data = request.get_data()
    obj = json.loads(data)
    return make_response(escape(str(obj)))

@app.route("/proc_37_6")
def process_37_6():
    cmd = request.args.get("cmd")
    ALLOWED_COMMANDS = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"], "uptime": ["uptime"]}
    if cmd not in ALLOWED_COMMANDS:
        return "Command not allowed", 403
    result = subprocess.run(ALLOWED_COMMANDS[cmd], capture_output=True)
    return result.stdout

@app.route("/ping_37_7")
def check_status_37_7():
    host = request.args.get("host")
    if not host or not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", "--", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_37_8")
def search_37_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    result = cursor.fetchall()
    return make_response(escape(str(result)))

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _safe_eval(expr):
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree.body)


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    raise ValueError("Unsupported expression")


@app.route("/calc_37_9")
def calculate_37_9():
    expr = request.args.get("expr")
    result = _safe_eval(expr)
    return str(result)
