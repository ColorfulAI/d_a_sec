"""Stress test module 44 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
import ast
import operator
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response, Response

app = Flask(__name__)

SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _safe_eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op = SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError("Unsupported operation")
        return op(_safe_eval_node(node.left), _safe_eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_eval_node(node.operand)
    raise ValueError("Unsupported expression")

ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}
ALLOWED_URLS = {"example": "https://example.com", "api": "https://api.example.com"}

@app.route("/query_44_0")
def query_db_44_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return Response(str(cursor.fetchall()), content_type="text/plain")

@app.route("/cmd_44_1")
def run_cmd_44_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    base_dir = os.path.abspath("data")
    safe_path = os.path.realpath(os.path.join(base_dir, safe_name))
    if not safe_path.startswith(base_dir + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        f.read()
    return "done"

@app.route("/read_44_2")
def read_file_44_2():
    path = request.args.get("path")
    base_dir = os.path.abspath("uploads")
    safe_path = os.path.realpath(os.path.join(base_dir, path))
    if not safe_path.startswith(base_dir + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return Response(f.read(), content_type="text/plain")

@app.route("/render_44_3")
def render_page_44_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_44_4")
def fetch_url_44_4():
    url_key = request.args.get("url")
    safe_url = ALLOWED_URLS.get(url_key)
    if safe_url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_44_5")
def load_data_44_5():
    data = request.get_data()
    return Response(str(json.loads(data)), content_type="text/plain")

@app.route("/proc_44_6")
def process_44_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True)
    return result.stdout

@app.route("/ping_44_7")
def check_status_44_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.-]*$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_44_8")
def search_44_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return Response(str(cursor.fetchall()), content_type="text/plain")

@app.route("/calc_44_9")
def calculate_44_9():
    expr = request.args.get("expr")
    tree = ast.parse(expr, mode='eval')
    result = _safe_eval_node(tree.body)
    return str(result)
