"""Stress test module 15 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import re
from markupsafe import escape
from flask import Flask, request, make_response

ALLOWED_READ_DIR = os.path.realpath("/var/data")
COMMAND_MAP = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}
FETCH_URLS = {
    "service_a": "https://api.example.com/a",
    "service_b": "https://api.example.com/b",
}

app = Flask(__name__)

@app.route("/query_15_0")
def query_db_15_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_15_1")
def run_cmd_15_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    result = subprocess.run(["cat", safe_name], capture_output=True, text=True)
    return result.stdout

@app.route("/read_15_2")
def read_file_15_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(ALLOWED_READ_DIR, os.path.basename(path)))
    if not safe_path.startswith(ALLOWED_READ_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_15_3")
def render_page_15_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_15_4")
def fetch_url_15_4():
    key = request.args.get("url")
    url = FETCH_URLS.get(key)
    if url is None:
        return "Invalid service", 400
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(url)
    return resp.read()

@app.route("/load_15_5")
def load_data_15_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_15_6")
def process_15_6():
    cmd = request.args.get("cmd")
    safe_cmd = COMMAND_MAP.get(cmd)
    if safe_cmd is None:
        return "Forbidden", 403
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_15_7")
def check_status_15_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_15_8")
def search_15_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_15_9")
def calculate_15_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
