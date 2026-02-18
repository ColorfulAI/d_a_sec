"""Stress test module 49 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import re
import json
import urllib.request
from flask import Flask, request, make_response, Response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "data"))

ALLOWED_URLS = {
    "example": "https://example.com/",
}

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "pwd": ["pwd"],
    "whoami": ["whoami"],
    "date": ["date"],
}

@app.route("/query_49_0")
def query_db_49_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return Response(str(cursor.fetchall()), content_type="text/plain")

@app.route("/cmd_49_1")
def run_cmd_49_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_49_2")
def read_file_49_2():
    filename = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, filename))
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return Response(f.read(), content_type="text/plain")

@app.route("/render_49_3")
def render_page_49_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_49_4")
def fetch_url_49_4():
    url_key = request.args.get("url")
    url = ALLOWED_URLS.get(url_key)
    if url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_49_5")
def load_data_49_5():
    data = request.get_data()
    return Response(str(json.loads(data)), content_type="text/plain")

@app.route("/proc_49_6")
def process_49_6():
    cmd_key = request.args.get("cmd")
    cmd_args = ALLOWED_COMMANDS.get(cmd_key)
    if cmd_args is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd_args, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_49_7")
def check_status_49_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_49_8")
def search_49_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return Response(str(cursor.fetchall()), content_type="text/plain")

@app.route("/calc_49_9")
def calculate_49_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
