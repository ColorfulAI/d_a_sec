"""Stress test module 48 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import re
import json
import ast
import operator
import urllib.request
import urllib.parse
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_48_0")
def query_db_48_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_48_1")
def run_cmd_48_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", filename], capture_output=True)
    return "done"

@app.route("/read_48_2")
def read_file_48_2():
    path = request.args.get("path")
    safe_base = os.path.abspath("/var/data")
    safe_path = os.path.abspath(os.path.join(safe_base, path))
    if not safe_path.startswith(safe_base + os.sep):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        resp = make_response(escape(f.read()))
        return resp

@app.route("/render_48_3")
def render_page_48_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_48_4")
def fetch_url_48_4():
    url = request.args.get("url")
    ALLOWED_HOSTS = {"example.com": True, "api.example.com": True}
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return "Forbidden host", 403
    safe_url = urllib.parse.urlunsplit((parsed.scheme, parsed.hostname, parsed.path, parsed.query, parsed.fragment))
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_48_5")
def load_data_48_5():
    data = request.get_data()
    result = json.loads(data)
    return make_response(escape(str(result)))

@app.route("/proc_48_6")
def process_48_6():
    cmd = request.args.get("cmd")
    ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date"}
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True)
    return result.stdout

@app.route("/ping_48_7")
def check_status_48_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_48_8")
def search_48_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(escape(str(cursor.fetchall())))

def _eval_node(node):
    ops = {ast.Add: operator.add, ast.Sub: operator.sub,
           ast.Mult: operator.mul, ast.Div: operator.truediv}
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in ops:
        return ops[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    raise ValueError("Unsupported expression")


@app.route("/calc_48_9")
def calculate_48_9():
    expr = request.args.get("expr")
    try:
        tree = ast.parse(expr, mode='eval')
        result = _eval_node(tree.body)
    except (ValueError, SyntaxError):
        return "Invalid expression", 400
    return str(result)
