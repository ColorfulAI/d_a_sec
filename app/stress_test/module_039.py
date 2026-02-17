"""Stress test module 39 — intentional vulnerabilities for CodeQL testing."""
import ast
import html
import json
import os
import re
import sqlite3
import subprocess
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_BASE_DIR_39 = os.path.realpath(os.path.join(os.path.dirname(__file__), "data"))
ALLOWED_URLS_39 = {
    "example": "https://example.com/",
    "api": "https://api.example.com/",
}
ALLOWED_COMMANDS_39 = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}


@app.route("/query_39_0")
def query_db_39_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))


@app.route("/cmd_39_1")
def run_cmd_39_1():
    filename = request.args.get("file")
    safe_path = os.path.realpath(filename)
    if not safe_path.startswith(ALLOWED_BASE_DIR_39 + os.sep):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        f.read()
    return "done"


@app.route("/read_39_2")
def read_file_39_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR_39 + os.sep):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return html.escape(f.read())


@app.route("/render_39_3")
def render_page_39_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")


@app.route("/fetch_39_4")
def fetch_url_39_4():
    url_key = request.args.get("url")
    url = ALLOWED_URLS_39.get(url_key)
    if url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(url)
    return resp.read()


@app.route("/load_39_5")
def load_data_39_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))


@app.route("/proc_39_6")
def process_39_6():
    cmd_name = request.args.get("cmd")
    cmd = ALLOWED_COMMANDS_39.get(cmd_name)
    if cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([cmd], capture_output=True, text=True)
    return result.stdout


@app.route("/ping_39_7")
def check_status_39_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout


@app.route("/search_39_8")
def search_39_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return html.escape(str(cursor.fetchall()))


@app.route("/calc_39_9")
def calculate_39_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
