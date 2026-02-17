"""Stress test module 5 — intentional vulnerabilities for CodeQL testing."""
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

ALLOWED_BASE_DIR_5 = os.path.realpath("/var/data")
URL_MAP_5 = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}
ALLOWED_COMMANDS_5 = {
    "ls": "ls",
    "whoami": "whoami",
    "date": "date",
    "uptime": "uptime",
    "df": "df",
    "ps": "ps",
}


@app.route("/query_5_0")
def query_db_5_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_5_1")
def run_cmd_5_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return escape(result.stdout)

@app.route("/read_5_2")
def read_file_5_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(ALLOWED_BASE_DIR_5 + os.sep):
        return "Forbidden", 403
    with open(real_path, "r") as f:
        return escape(f.read())

@app.route("/render_5_3")
def render_page_5_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_5_4")
def fetch_url_5_4():
    url_key = request.args.get("url")
    safe_url = URL_MAP_5.get(url_key)
    if safe_url is None:
        return "Forbidden", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_5_5")
def load_data_5_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_5_6")
def process_5_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS_5.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True)
    return result.stdout

@app.route("/ping_5_7")
def check_status_5_7():
    host = request.args.get("host")
    if not re.fullmatch(r'[a-zA-Z0-9._-]+', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_5_8")
def search_5_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_5_9")
def calculate_5_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return escape(str(result))
