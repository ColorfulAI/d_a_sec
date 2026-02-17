"""Stress test module 18 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import re
import urllib.request
from urllib.parse import urlparse
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("/var/data/files")
ALLOWED_URLS = {
    "http://127.0.0.1/": "http://127.0.0.1/",
    "http://localhost/": "http://localhost/",
    "https://127.0.0.1/": "https://127.0.0.1/",
    "https://localhost/": "https://localhost/",
}
ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}


@app.route("/query_18_0")
def query_db_18_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))


@app.route("/cmd_18_1")
def run_cmd_18_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", "--", filename], capture_output=True, check=False)
    return "done"


@app.route("/read_18_2")
def read_file_18_2():
    path = request.args.get("path")
    abs_path = os.path.abspath(os.path.join(SAFE_BASE_DIR, path))
    if not abs_path.startswith(SAFE_BASE_DIR):
        return "Forbidden", 403
    with open(abs_path, "r") as f:
        content = f.read()
    return make_response(escape(content))


@app.route("/render_18_3")
def render_page_18_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")


@app.route("/fetch_18_4")
def fetch_url_18_4():
    url = request.args.get("url")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return "Invalid scheme", 403
    lookup_key = parsed.scheme + "://" + parsed.hostname + "/"
    safe_url = ALLOWED_URLS.get(lookup_key)
    if safe_url is None:
        return "Forbidden host", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()


@app.route("/load_18_5")
def load_data_18_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))))


@app.route("/proc_18_6")
def process_18_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True, check=False)
    return result.stdout


@app.route("/ping_18_7")
def check_status_18_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout


@app.route("/search_18_8")
def search_18_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(escape(str(cursor.fetchall())))


@app.route("/calc_18_9")
def calculate_18_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return make_response(escape(str(result)))
