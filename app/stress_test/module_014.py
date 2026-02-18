"""Stress test module 14 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import re
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("uploads")

@app.route("/query_14_0")
def query_db_14_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())), 200, {"Content-Type": "text/plain"})

@app.route("/cmd_14_1")
def run_cmd_14_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True, check=False)
    return make_response(result.stdout, 200, {"Content-Type": "text/plain"})

@app.route("/read_14_2")
def read_file_14_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return make_response(escape(f.read()), 200, {"Content-Type": "text/plain"})

@app.route("/render_14_3")
def render_page_14_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_14_4")
def fetch_url_14_4():
    return make_response("URL fetching is disabled", 403)

@app.route("/load_14_5")
def load_data_14_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))), 200, {"Content-Type": "text/plain"})

@app.route("/proc_14_6")
def process_14_6():
    return make_response("Command execution is disabled", 403)

@app.route("/ping_14_7")
def check_status_14_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, check=False)
    return make_response(result.stdout, 200, {"Content-Type": "text/plain"})

@app.route("/search_14_8")
def search_14_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(escape(str(cursor.fetchall())), 200, {"Content-Type": "text/plain"})

@app.route("/calc_14_9")
def calculate_14_9():
    return make_response("Expression evaluation is disabled", 403)
