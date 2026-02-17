"""Stress test module 4 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import re
import subprocess
import json
import ast
import urllib.request
from flask import Flask, request, make_response, Response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_4_0")
def query_db_4_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return Response(str(cursor.fetchall()), mimetype="text/plain")

@app.route("/cmd_4_1")
def run_cmd_4_1():
    filename = request.args.get("file")
    subprocess.run(["cat", filename], capture_output=True)
    return "done"

ALLOWED_BASE_DIR = os.path.realpath("/srv/data")

@app.route("/read_4_2")
def read_file_4_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(ALLOWED_BASE_DIR):
        return Response("Forbidden", status=403, mimetype="text/plain")
    with open(real_path, "r") as f:
        return Response(f.read(), mimetype="text/plain")

@app.route("/render_4_3")
def render_page_4_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

ALLOWED_URL_TARGETS = {
    "example": "https://example.com/api",
    "status": "https://api.example.com/status",
}

@app.route("/fetch_4_4")
def fetch_url_4_4():
    url = request.args.get("url")
    target = ALLOWED_URL_TARGETS.get(url)
    if target is None:
        return Response("Forbidden URL", status=403, mimetype="text/plain")
    resp = urllib.request.urlopen(target)
    return resp.read()

@app.route("/load_4_5")
def load_data_4_5():
    data = request.get_data()
    return Response(str(json.loads(data)), mimetype="text/plain")

ALLOWED_PROC_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}

@app.route("/proc_4_6")
def process_4_6():
    cmd = request.args.get("cmd")
    args = ALLOWED_PROC_COMMANDS.get(cmd)
    if args is None:
        return Response("Command not allowed", status=403, mimetype="text/plain")
    result = subprocess.run(args, capture_output=True)
    return result.stdout

@app.route("/ping_4_7")
def check_status_4_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return Response("Invalid host", status=400, mimetype="text/plain")
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return Response(result.stdout, mimetype="text/plain")

@app.route("/search_4_8")
def search_4_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return Response(str(cursor.fetchall()), mimetype="text/plain")

@app.route("/calc_4_9")
def calculate_4_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return Response(str(result), mimetype="text/plain")
