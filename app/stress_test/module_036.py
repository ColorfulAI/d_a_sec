"""Stress test module 36 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_DIR = os.path.realpath("/safe")

@app.route("/query_36_0")
def query_db_36_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_36_1")
def run_cmd_36_1():
    filename = request.args.get("file")
    abs_path = os.path.realpath(os.path.join(SAFE_DIR, filename))
    if not abs_path.startswith(SAFE_DIR + os.sep):
        return "Invalid filename", 400
    with open(abs_path, "r") as f:
        f.read()
    return "done"

@app.route("/read_36_2")
def read_file_36_2():
    path = request.args.get("path")
    abs_path = os.path.realpath(os.path.join(SAFE_DIR, path))
    if not abs_path.startswith(SAFE_DIR + os.sep):
        return "Forbidden", 403
    with open(abs_path, "r") as f:
        return str(escape(f.read()))

@app.route("/render_36_3")
def render_page_36_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_36_4")
def fetch_url_36_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_36_5")
def load_data_36_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_36_6")
def process_36_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_36_7")
def check_status_36_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_36_8")
def search_36_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_36_9")
def calculate_36_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
