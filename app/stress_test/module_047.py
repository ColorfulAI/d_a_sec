"""Stress test module 47 — intentional vulnerabilities for CodeQL testing."""
import ast
import json
import os
import re
import sqlite3
import subprocess
import urllib.request

from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("/var/data")
ALLOWED_URLS = {
    "example": "https://example.com/api",
    "status": "https://api.example.com/status",
}
ALLOWED_COMMANDS = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"], "uptime": ["uptime"]}


@app.route("/query_47_0")
def query_db_47_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_47_1")
def run_cmd_47_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9._\-/]+$', filename):
        return "invalid filename", 400
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_47_2")
def read_file_47_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(SAFE_BASE_DIR + os.sep):
        return "access denied", 403
    with open(safe_path, "r") as f:
        return str(escape(f.read()))

@app.route("/render_47_3")
def render_page_47_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_47_4")
def fetch_url_47_4():
    url_key = request.args.get("url")
    target = ALLOWED_URLS.get(url_key)
    if target is None:
        return "url not allowed", 403
    resp = urllib.request.urlopen(target)
    return resp.read()

@app.route("/load_47_5")
def load_data_47_5():
    data = request.get_data()
    return str(escape(str(json.loads(data))))

@app.route("/proc_47_6")
def process_47_6():
    cmd = request.args.get("cmd")
    cmd_list = ALLOWED_COMMANDS.get(cmd)
    if cmd_list is None:
        return "command not allowed", 403
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_47_7")
def check_status_47_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_47_8")
def search_47_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(escape(str(cursor.fetchall())))

@app.route("/calc_47_9")
def calculate_47_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
