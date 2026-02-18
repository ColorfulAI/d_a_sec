"""Stress test module 32 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import json
import os
import re
import subprocess
import ast
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

ALLOWED_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}

app = Flask(__name__)

@app.route("/query_32_0")
def query_db_32_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_32_1")
def run_cmd_32_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, check=False)
    return result.stdout

@app.route("/read_32_2")
def read_file_32_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_32_3")
def render_page_32_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_32_4")
def fetch_url_32_4():
    url_key = request.args.get("url")
    target = ALLOWED_URLS.get(url_key)
    if target is None:
        return "Forbidden", 403
    resp = urllib.request.urlopen(target)
    return resp.read()

@app.route("/load_32_5")
def load_data_32_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_32_6")
def process_32_6():
    return "Command execution disabled", 403

@app.route("/ping_32_7")
def check_status_32_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout

@app.route("/search_32_8")
def search_32_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_32_9")
def calculate_32_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return escape(str(result))
