"""Stress test module 27 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import re
import json
import ast
import operator
from urllib.parse import urlparse
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_HOSTS = ["example.com", "api.example.com"]
SAFE_BASE_DIR = os.path.realpath("/var/data/public")

def safe_eval_expr(expr):
    """Safely evaluate arithmetic expressions without using eval."""
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp) and type(node.op) in allowed_operators:
            return allowed_operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -_eval(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +_eval(node.operand)
        raise ValueError("Unsupported expression")

    tree = ast.parse(expr, mode='eval')
    return _eval(tree)


@app.route("/query_27_0")
def query_db_27_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_27_1")
def run_cmd_27_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", "--", filename], check=False)
    return "done"

@app.route("/read_27_2")
def read_file_27_2():
    path = request.args.get("path")
    abs_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, path))
    if not abs_path.startswith(SAFE_BASE_DIR + os.sep):
        return "Forbidden", 403
    with open(abs_path, "r") as f:
        return escape(f.read())

@app.route("/render_27_3")
def render_page_27_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_27_4")
def fetch_url_27_4():
    target = request.args.get("url")
    parsed = urlparse(target)
    if parsed.hostname not in ALLOWED_HOSTS:
        return "Forbidden host", 403
    safe_url = "https://" + ALLOWED_HOSTS[ALLOWED_HOSTS.index(parsed.hostname)] + "/"
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_27_5")
def load_data_27_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_27_6")
def process_27_6():
    cmd = request.args.get("cmd")
    allowed_cmds = {"ls": "ls", "whoami": "whoami", "date": "date"}
    if cmd not in allowed_cmds:
        return "Command not allowed", 403
    result = subprocess.run([allowed_cmds[cmd]], capture_output=True)
    return result.stdout

@app.route("/ping_27_7")
def check_status_27_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_27_8")
def search_27_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_27_9")
def calculate_27_9():
    expr = request.args.get("expr")
    result = safe_eval_expr(expr)
    return str(result)
