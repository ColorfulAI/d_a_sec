"""Stress test module 9 — intentional vulnerabilities for CodeQL testing."""
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

ALLOWED_BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "data"))
ALLOWED_URL_TARGETS = {"example": "https://example.com", "api": "https://api.example.com"}
ALLOWED_COMMANDS = {"ls": ["ls"], "date": ["date"], "whoami": ["whoami"], "uptime": ["uptime"]}


@app.route("/query_9_0")
def query_db_9_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))


@app.route("/cmd_9_1")
def run_cmd_9_1():
    filename = request.args.get("file")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, filename))
    if not safe_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        f.read()
    return "done"


@app.route("/read_9_2")
def read_file_9_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, path))
    if not safe_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return escape(f.read())


@app.route("/render_9_3")
def render_page_9_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")


@app.route("/fetch_9_4")
def fetch_url_9_4():
    target = request.args.get("url")
    safe_url = ALLOWED_URL_TARGETS.get(target)
    if safe_url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()


@app.route("/load_9_5")
def load_data_9_5():
    data = request.get_data()
    return escape(str(json.loads(data)))


@app.route("/proc_9_6")
def process_9_6():
    cmd = request.args.get("cmd")
    cmd_list = ALLOWED_COMMANDS.get(cmd)
    if cmd_list is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    return escape(result.stdout)


@app.route("/ping_9_7")
def check_status_9_7():
    host = request.args.get("host")
    if not host or not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return escape(result.stdout)


@app.route("/search_9_8")
def search_9_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))


@app.route("/calc_9_9")
def calculate_9_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return escape(str(result))
