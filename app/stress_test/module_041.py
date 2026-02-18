"""Stress test module 41 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import html
import ast
import re
import urllib.request
from flask import Flask, request, make_response

ALLOWED_BASE_DIR = os.path.abspath("/var/data")
ALLOWED_FILES = {"readme": "readme.txt", "config": "config.json", "data": "data.csv"}

app = Flask(__name__)

@app.route("/query_41_0")
def query_db_41_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_41_1")
def run_cmd_41_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], capture_output=True)
    return "done"

@app.route("/read_41_2")
def read_file_41_2():
    key = request.args.get("path")
    if key not in ALLOWED_FILES:
        return "Forbidden", 403
    safe_path = os.path.join(ALLOWED_BASE_DIR, ALLOWED_FILES[key])
    with open(safe_path, "r") as f:
        return html.escape(f.read())

@app.route("/render_41_3")
def render_page_41_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_41_4")
def fetch_url_41_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_41_5")
def load_data_41_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_41_6")
def process_41_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_41_7")
def check_status_41_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_41_8")
def search_41_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_41_9")
def calculate_41_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
