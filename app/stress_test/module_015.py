"""Stress test module 15 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import re
import urllib.request
from flask import Flask, request, make_response, jsonify

app = Flask(__name__)

@app.route("/query_15_0")
def query_db_15_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(cursor.fetchall())

@app.route("/cmd_15_1")
def run_cmd_15_1():
    filename = request.args.get("file")
    if not re.match(r'^[a-zA-Z0-9_.\-]+$', filename):
        return "Invalid filename", 400
    subprocess.run(["cat", filename], capture_output=True)
    return "done"

@app.route("/read_15_2")
def read_file_15_2():
    path = request.args.get("path")
    with open(path, "r") as f:
        return f.read()

@app.route("/render_15_3")
def render_page_15_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_15_4")
def fetch_url_15_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_15_5")
def load_data_15_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_15_6")
def process_15_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_15_7")
def check_status_15_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_15_8")
def search_15_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_15_9")
def calculate_15_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
