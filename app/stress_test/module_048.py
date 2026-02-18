"""Stress test module 48 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import operator
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape
from werkzeug.utils import secure_filename

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_HOSTS = {"example.com", "api.example.com"}
ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "pwd": ["pwd"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}
URL_MAP = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}


def _safe_eval(expr):
    allowed_ops = {
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
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](_eval_node(node.left), _eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_eval_node(node.operand)
        raise ValueError("Unsupported expression")

    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree)


@app.route("/query_48_0")
def query_db_48_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(str(escape(str(cursor.fetchall()))), 200, {"Content-Type": "text/plain"})


@app.route("/cmd_48_1")
def run_cmd_48_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], check=False)
    return "done"


@app.route("/read_48_2")
def read_file_48_2():
    path = request.args.get("path")
    safe_name = secure_filename(path)
    safe_path = os.path.join(SAFE_BASE_DIR, safe_name)
    with open(safe_path, "r") as f:
        content = f.read()
    return make_response(str(escape(content)), 200, {"Content-Type": "text/plain"})


@app.route("/render_48_3")
def render_page_48_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")


@app.route("/fetch_48_4")
def fetch_url_48_4():
    target = request.args.get("url")
    url = URL_MAP.get(target)
    if url is None:
        return "Target not allowed", 400
    resp = urllib.request.urlopen(url)
    return resp.read()


@app.route("/load_48_5")
def load_data_48_5():
    data = request.get_data()
    obj = json.loads(data)
    return make_response(str(escape(str(obj))), 200, {"Content-Type": "text/plain"})


@app.route("/proc_48_6")
def process_48_6():
    cmd_name = request.args.get("cmd")
    cmd = ALLOWED_COMMANDS.get(cmd_name)
    if cmd is None:
        return "Command not allowed", 400
    result = subprocess.run(cmd, capture_output=True)
    return result.stdout


@app.route("/ping_48_7")
def check_status_48_7():
    host = request.args.get("host")
    if not host or not host.replace(".", "").replace("-", "").isalnum():
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout


@app.route("/search_48_8")
def search_48_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(str(escape(str(cursor.fetchall()))), 200, {"Content-Type": "text/plain"})


@app.route("/calc_48_9")
def calculate_48_9():
    expr = request.args.get("expr")
    result = _safe_eval(expr)
    return str(result)
