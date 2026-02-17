"""Stress test module 27 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import re
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_27_0")
def query_db_27_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_27_1")
def run_cmd_27_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", filename], capture_output=True)
    return "done"

@app.route("/read_27_2")
def read_file_27_2():
    path = request.args.get("path")
    safe_base = os.path.realpath("/var/data")
    real_path = os.path.realpath(path)
    if not real_path.startswith(safe_base):
        return "Forbidden", 403
    with open(real_path, "r") as f:
        return escape(f.read())

@app.route("/render_27_3")
def render_page_27_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_27_4")
def fetch_url_27_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_27_5")
def load_data_27_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_27_6")
def process_27_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_27_7")
def check_status_27_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_27_8")
def search_27_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_27_9")
def calculate_27_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
