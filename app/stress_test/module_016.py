"""Stress test module 16 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import json
import re
import ast
import subprocess
import urllib.request
from html import escape
from flask import Flask, request, make_response

ALLOWED_BASE_DIR = "/var/data"
ALLOWED_URLS = {"example": "https://example.com", "api": "https://api.example.com"}
ALLOWED_COMMANDS = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"]}

app = Flask(__name__)

@app.route("/query_16_0")
def query_db_16_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_16_1")
def run_cmd_16_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, filename))
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        f.read()
    return "done"

@app.route("/read_16_2")
def read_file_16_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, path))
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_16_3")
def render_page_16_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_16_4")
def fetch_url_16_4():
    url_key = request.args.get("url")
    if url_key not in ALLOWED_URLS:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(ALLOWED_URLS[url_key])
    return resp.read()

@app.route("/load_16_5")
def load_data_16_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_16_6")
def process_16_6():
    cmd = request.args.get("cmd")
    if cmd not in ALLOWED_COMMANDS:
        return "Command not allowed", 403
    result = subprocess.run(ALLOWED_COMMANDS[cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_16_7")
def check_status_16_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_16_8")
def search_16_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_16_9")
def calculate_16_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
