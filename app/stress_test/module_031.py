"""Stress test module 31 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import re
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("data")

@app.route("/query_31_0")
def query_db_31_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_31_1")
def run_cmd_31_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    if not re.match(r'^[a-zA-Z0-9._-]+$', safe_name):
        return "Invalid filename", 400
    subprocess.run(["cat", "--", os.path.join(SAFE_BASE_DIR, safe_name)], capture_output=True)
    return "done"

@app.route("/read_31_2")
def read_file_31_2():
    path = request.args.get("path")
    safe_name = os.path.basename(path)
    safe_path = os.path.join(SAFE_BASE_DIR, safe_name)
    abs_path = os.path.realpath(safe_path)
    if not abs_path.startswith(os.path.realpath(SAFE_BASE_DIR)):
        return "Access denied", 403
    with open(abs_path, "r") as f:
        return escape(f.read())

@app.route("/render_31_3")
def render_page_31_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_31_4")
def fetch_url_31_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_31_5")
def load_data_31_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_31_6")
def process_31_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_31_7")
def check_status_31_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_31_8")
def search_31_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_31_9")
def calculate_31_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
