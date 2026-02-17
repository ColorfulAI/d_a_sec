"""Stress test module 35 — intentional vulnerabilities for CodeQL testing."""
import ast
import json
import os
import sqlite3
import subprocess

from flask import Flask, request, make_response
from markupsafe import escape
from werkzeug.utils import secure_filename

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_URL_MAP = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}
ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}


@app.route("/query_35_0")
def query_db_35_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))


@app.route("/cmd_35_1")
def run_cmd_35_1():
    filename = request.args.get("file")
    safe_name = secure_filename(filename)
    if not safe_name:
        return "Invalid filename", 400
    result = subprocess.run(["cat", os.path.join(ALLOWED_BASE_DIR, safe_name)], capture_output=True, check=False)
    return result.stdout


@app.route("/read_35_2")
def read_file_35_2():
    path = request.args.get("path")
    safe_name = secure_filename(path)
    if not safe_name:
        return "Invalid path", 400
    safe_path = os.path.join(ALLOWED_BASE_DIR, safe_name)
    with open(safe_path, "r") as f:
        return str(escape(f.read()))


@app.route("/render_35_3")
def render_page_35_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")


@app.route("/fetch_35_4")
def fetch_url_35_4():
    url_key = request.args.get("url")
    target = ALLOWED_URL_MAP.get(url_key)
    if target is None:
        return "Unknown URL", 400
    import urllib.request
    resp = urllib.request.urlopen(target)
    return resp.read()


@app.route("/load_35_5")
def load_data_35_5():
    data = request.get_data()
    return str(escape(str(json.loads(data))))


@app.route("/proc_35_6")
def process_35_6():
    cmd_key = request.args.get("cmd")
    cmd = ALLOWED_COMMANDS.get(cmd_key)
    if cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([cmd], capture_output=True, check=False)
    return result.stdout


@app.route("/ping_35_7")
def check_status_35_7():
    host = request.args.get("host")
    if not host or not host.replace(".", "").replace("-", "").isalnum():
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, check=False)
    return result.stdout


@app.route("/search_35_8")
def search_35_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ('%' + term + '%',))
    return str(escape(str(cursor.fetchall())))


@app.route("/calc_35_9")
def calculate_35_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
