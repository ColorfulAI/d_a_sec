"""Stress test module 35 — intentional vulnerabilities for CodeQL testing."""
import ast
import json
import os
import re
import sqlite3
import subprocess
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_HOSTS = {"example.com", "api.example.com"}


@app.route("/query_35_0")
def query_db_35_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_35_1")
def run_cmd_35_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_35_2")
def read_file_35_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(SAFE_BASE_DIR):
        return "Access denied", 403
    with open(real_path, "r") as f:
        return escape(f.read())

@app.route("/render_35_3")
def render_page_35_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_35_4")
def fetch_url_35_4():
    url = request.args.get("url")
    if not url:
        return "Missing URL", 400
    return "URL fetching disabled for security", 403

@app.route("/load_35_5")
def load_data_35_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime", "uname": "uname"}


@app.route("/proc_35_6")
def process_35_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_35_7")
def check_status_35_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_35_8")
def search_35_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_35_9")
def calculate_35_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
