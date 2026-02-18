"""Stress test module 45 — intentional vulnerabilities for CodeQL testing."""
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

SAFE_DATA_DIR = os.path.abspath("/var/data")


@app.route("/query_45_0")
def query_db_45_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_45_1")
def run_cmd_45_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", "--", filename], capture_output=True, check=False)
    return "done"

@app.route("/read_45_2")
def read_file_45_2():
    path = request.args.get("path")
    abs_path = os.path.realpath(os.path.join(SAFE_DATA_DIR, path))
    if not abs_path.startswith(SAFE_DATA_DIR + os.sep):
        return "Forbidden", 403
    with open(abs_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/render_45_3")
def render_page_45_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_45_4")
def fetch_url_45_4():
    url = request.args.get("url")
    allowed_hosts = ["api.example.com"]
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in allowed_hosts or parsed.scheme != "https":
        return "URL not allowed", 403
    safe_url = urllib.parse.urlunparse(parsed)
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_45_5")
def load_data_45_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))))

@app.route("/proc_45_6")
def process_45_6():
    cmd = request.args.get("cmd")
    allowed_cmds = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"]}
    if cmd not in allowed_cmds:
        return "Command not allowed", 403
    result = subprocess.run(allowed_cmds[cmd], capture_output=True, check=False)
    return result.stdout

@app.route("/ping_45_7")
def check_status_45_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, check=False)
    return result.stdout

@app.route("/search_45_8")
def search_45_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/calc_45_9")
def calculate_45_9():
    expr = request.args.get("expr")
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](_eval_node(node.left), _eval_node(node.right))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_eval_node(node.operand)
        else:
            raise ValueError("Unsafe expression")
    tree = ast.parse(expr, mode='eval')
    result = _eval_node(tree)
    return str(result)
