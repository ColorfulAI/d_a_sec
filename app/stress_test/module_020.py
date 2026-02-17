"""Stress test module 20 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("/var/data")
ALLOWED_FILES = {"config": "config.txt", "readme": "readme.txt", "log": "log.txt"}

@app.route("/query_20_0")
def query_db_20_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_20_1")
def run_cmd_20_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    result = subprocess.run(["cat", safe_name], capture_output=True)
    return result.stdout

@app.route("/read_20_2")
def read_file_20_2():
    path = request.args.get("path")
    filename = ALLOWED_FILES.get(path)
    if filename is None:
        return "forbidden", 403
    safe_path = os.path.join(SAFE_BASE_DIR, filename)
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_20_3")
def render_page_20_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_20_4")
def fetch_url_20_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_20_5")
def load_data_20_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_20_6")
def process_20_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_20_7")
def check_status_20_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_20_8")
def search_20_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_20_9")
def calculate_20_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
