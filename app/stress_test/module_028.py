"""Stress test module 28 — intentional vulnerabilities for CodeQL testing."""
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

ALLOWED_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_URLS = {
    "service1": "https://api.example.com/service1",
    "service2": "https://api.example.com/service2",
}
ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date"}
ALLOWED_FILES = {"report": "report.txt", "log": "app.log", "config": "config.json"}


@app.route("/query_28_0")
def query_db_28_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))


@app.route("/cmd_28_1")
def run_cmd_28_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    full_path = os.path.join(ALLOWED_BASE_DIR, safe_name)
    subprocess.run(["cat", full_path], capture_output=True)
    return "done"


@app.route("/read_28_2")
def read_file_28_2():
    file_key = request.args.get("path")
    filename = ALLOWED_FILES.get(file_key)
    if filename is None:
        return "Forbidden", 403
    real_path = os.path.join(ALLOWED_BASE_DIR, filename)
    with open(real_path, "r") as f:
        return escape(f.read())


@app.route("/render_28_3")
def render_page_28_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")


@app.route("/fetch_28_4")
def fetch_url_28_4():
    url_key = request.args.get("url")
    target_url = ALLOWED_URLS.get(url_key)
    if target_url is None:
        return "Forbidden", 403
    resp = urllib.request.urlopen(target_url)
    return resp.read()


@app.route("/load_28_5")
def load_data_28_5():
    data = request.get_data()
    return escape(str(json.loads(data)))


@app.route("/proc_28_6")
def process_28_6():
    cmd_name = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd_name)
    if safe_cmd is None:
        return "Forbidden", 403
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout


@app.route("/ping_28_7")
def check_status_28_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout


@app.route("/search_28_8")
def search_28_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))


@app.route("/calc_28_9")
def calculate_28_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
