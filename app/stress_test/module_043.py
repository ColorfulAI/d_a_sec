"""Stress test module 43 — intentional vulnerabilities for CodeQL testing."""
import re
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_43_0")
def query_db_43_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_43_1")
def run_cmd_43_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", filename], capture_output=True)
    return "done"

@app.route("/read_43_2")
def read_file_43_2():
    path = request.args.get("path")
    safe_dir = os.path.abspath("/var/data")
    full_path = os.path.abspath(os.path.join(safe_dir, path))
    if not full_path.startswith(safe_dir):
        return "Forbidden", 403
    with open(full_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/render_43_3")
def render_page_43_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_43_4")
def fetch_url_43_4():
    target = request.args.get("url")
    url_map = {
        "example": "https://example.com",
        "api": "https://api.example.com",
    }
    safe_url = url_map.get(target)
    if safe_url is None:
        return "Invalid target", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_43_5")
def load_data_43_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))))

@app.route("/proc_43_6")
def process_43_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_43_7")
def check_status_43_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_43_8")
def search_43_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_43_9")
def calculate_43_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
