"""Stress test module 10 — intentional vulnerabilities for CodeQL testing."""
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


@app.route("/query_10_0")
def query_db_10_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))


@app.route("/cmd_10_1")
def run_cmd_10_1():
    filename = request.args.get("file")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, filename))
    if not safe_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        f.read()
    return "done"


@app.route("/read_10_2")
def read_file_10_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, path))
    if not safe_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return escape(f.read())


@app.route("/render_10_3")
def render_page_10_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")


@app.route("/fetch_10_4")
def fetch_url_10_4():
    target = request.args.get("url")
    safe_url = ALLOWED_URL_TARGETS.get(target)
    if safe_url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()


@app.route("/load_10_5")
def load_data_10_5():
    data = request.get_data()
    return escape(str(json.loads(data)))


@app.route("/proc_10_6")
def process_10_6():
    cmd = request.args.get("cmd")
    cmd_list = ALLOWED_COMMANDS.get(cmd)
    if cmd_list is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    return escape(result.stdout)


@app.route("/ping_10_7")
def check_status_10_7():
    host = request.args.get("host")
    if not host or not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return escape(result.stdout)


@app.route("/search_10_8")
def search_10_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))


@app.route("/calc_10_9")
def calculate_10_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return escape(str(result))
