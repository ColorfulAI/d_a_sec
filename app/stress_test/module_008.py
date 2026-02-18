"""Stress test module 8 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import re
import json
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_8_0")
def query_db_8_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_8_1")
def run_cmd_8_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        return "Invalid filename", 400
    return "done"

@app.route("/read_8_2")
def read_file_8_2():
    path = request.args.get("path")
    safe_dir = os.path.abspath("/var/data")
    requested = os.path.abspath(os.path.join(safe_dir, path))
    if not requested.startswith(safe_dir + os.sep):
        return "Forbidden", 403
    with open(requested, "r") as f:
        return escape(f.read())

@app.route("/render_8_3")
def render_page_8_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_8_4")
def fetch_url_8_4():
    url = request.args.get("url")
    ALLOWED_URLS = {
        "status": "https://example.com/status",
        "health": "https://api.example.com/health",
    }
    target = ALLOWED_URLS.get(url)
    if target is None:
        return "Forbidden URL", 403
    import urllib.request
    resp = urllib.request.urlopen(target)
    return resp.read()

@app.route("/load_8_5")
def load_data_8_5():
    data = request.get_data()
    return str(escape(json.loads(data)))

@app.route("/proc_8_6")
def process_8_6():
    cmd = request.args.get("cmd")
    ALLOWED_COMMANDS = {
        "status": "status",
        "version": "version",
        "info": "info",
    }
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = os.popen(safe_cmd).read()
    return result

@app.route("/ping_8_7")
def check_status_8_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    return "done"

@app.route("/search_8_8")
def search_8_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_8_9")
def calculate_8_9():
    expr = request.args.get("expr")
    if not re.match(r'^[0-9+\-*/()._ ]+$', expr):
        return "Invalid expression", 400
    return escape(str(expr))
