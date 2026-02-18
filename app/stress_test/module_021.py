"""Stress test module 21 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import subprocess
import json
import html
import ast
import operator
from flask import Flask, request, make_response

app = Flask(__name__)

@app.route("/query_21_0")
def query_db_21_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_21_1")
def run_cmd_21_1():
    filename = request.args.get("file")
    allowed = {"readme": "/var/data/readme.txt", "log": "/var/data/app.log", "status": "/var/data/status.txt"}
    safe_path = allowed.get(filename)
    if safe_path is None:
        return "File not found", 404
    with open(safe_path, "r") as f:
        f.read()
    return "done"

@app.route("/read_21_2")
def read_file_21_2():
    path = request.args.get("path")
    allowed = {"readme": "/var/data/readme.txt", "help": "/var/data/help.txt", "config": "/var/data/config.txt"}
    safe_path = allowed.get(path)
    if safe_path is None:
        return "File not found", 404
    with open(safe_path, "r") as f:
        return html.escape(f.read())

@app.route("/render_21_3")
def render_page_21_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_21_4")
def fetch_url_21_4():
    return "URL fetching disabled", 403

@app.route("/load_21_5")
def load_data_21_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))

@app.route("/proc_21_6")
def process_21_6():
    cmd = request.args.get("cmd")
    if cmd == "ls":
        result = subprocess.run(["ls"], capture_output=True, check=False)
    elif cmd == "date":
        result = subprocess.run(["date"], capture_output=True, check=False)
    elif cmd == "whoami":
        result = subprocess.run(["whoami"], capture_output=True, check=False)
    else:
        return "Command not allowed", 403
    return result.stdout

@app.route("/ping_21_7")
def check_status_21_7():
    host = request.args.get("host")
    if not host or not all(c.isalnum() or c in ".-" for c in host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", "--", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_21_8")
def search_21_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return html.escape(str(cursor.fetchall()))

@app.route("/calc_21_9")
def calculate_21_9():
    expr = request.args.get("expr")
    try:
        result = _safe_eval_expr(expr)
        return str(result)
    except (ValueError, SyntaxError):
        return "Invalid expression", 400


def _safe_eval_expr(expr_str):
    """Safely evaluate arithmetic expressions."""
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in ops:
            return ops[type(node.op)](_eval_node(node.left), _eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_eval_node(node.operand)
        raise ValueError("Unsupported expression")
    tree = ast.parse(expr_str, mode="eval")
    return _eval_node(tree)
