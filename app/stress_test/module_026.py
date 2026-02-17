"""Stress test module 26 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("data")

ALLOWED_FILES = {
    "readme": "readme.txt",
    "config": "config.txt",
    "log": "app.log",
}


@app.route("/query_26_0")
def query_db_26_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_26_1")
def run_cmd_26_1():
    key = request.args.get("file")
    filename = ALLOWED_FILES.get(key)
    if filename is None:
        return "File not allowed", 400
    safe_path = os.path.join(SAFE_BASE_DIR, filename)
    with open(safe_path, "r") as f:
        f.read()
    return "done"

@app.route("/read_26_2")
def read_file_26_2():
    key = request.args.get("path")
    filename = ALLOWED_FILES.get(key)
    if filename is None:
        return "File not allowed", 400
    safe_path = os.path.join(SAFE_BASE_DIR, filename)
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_26_3")
def render_page_26_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_26_4")
def fetch_url_26_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_26_5")
def load_data_26_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_26_6")
def process_26_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_26_7")
def check_status_26_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_26_8")
def search_26_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_26_9")
def calculate_26_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
