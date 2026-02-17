"""Stress test module 22 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import re
import urllib.request
from flask import Flask, request, make_response, jsonify

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data/files")

@app.route("/query_22_0")
def query_db_22_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    rows = cursor.fetchall()
    return jsonify(rows)

@app.route("/cmd_22_1")
def run_cmd_22_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", filename], capture_output=True)
    return "done"

@app.route("/read_22_2")
def read_file_22_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(SAFE_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        content = f.read()
    return jsonify({"content": content})

@app.route("/render_22_3")
def render_page_22_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_22_4")
def fetch_url_22_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_22_5")
def load_data_22_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_22_6")
def process_22_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_22_7")
def check_status_22_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_22_8")
def search_22_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_22_9")
def calculate_22_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
