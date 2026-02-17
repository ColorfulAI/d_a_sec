"""Stress test module 29 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import json
import os
import subprocess
import re
import html
import ast
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

SAFE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
ALLOWED_HOSTS = {"example.com": "https://example.com", "api.example.com": "https://api.example.com"}
ALLOWED_COMMANDS = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"]}

@app.route("/query_29_0")
def query_db_29_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_29_1")
def run_cmd_29_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_29_2")
def read_file_29_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(SAFE_DIR, path))
    if not safe_path.startswith(SAFE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return html.escape(f.read())

@app.route("/render_29_3")
def render_page_29_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_29_4")
def fetch_url_29_4():
    url_key = request.args.get("url")
    if url_key not in ALLOWED_HOSTS:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(ALLOWED_HOSTS[url_key])
    return resp.read()

@app.route("/load_29_5")
def load_data_29_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))

@app.route("/proc_29_6")
def process_29_6():
    cmd = request.args.get("cmd")
    if cmd not in ALLOWED_COMMANDS:
        return "Command not allowed", 403
    result = subprocess.run(ALLOWED_COMMANDS[cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_29_7")
def check_status_29_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_29_8")
def search_29_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return html.escape(str(cursor.fetchall()))

@app.route("/calc_29_9")
def calculate_29_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return html.escape(str(result))
