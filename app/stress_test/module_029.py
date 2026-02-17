"""Stress test module 29 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import html
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

@app.route("/query_29_0")
def query_db_29_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_29_1")
def run_cmd_29_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    result = subprocess.run(["cat", safe_name], capture_output=True, text=True)
    return result.stdout

@app.route("/read_29_2")
def read_file_29_2():
    path = request.args.get("path")
    safe_dir = os.path.realpath("/var/data")
    real_path = os.path.realpath(os.path.join(safe_dir, path))
    if not real_path.startswith(safe_dir):
        return "Access denied", 403
    with open(real_path, "r") as f:
        return html.escape(f.read())

@app.route("/render_29_3")
def render_page_29_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_29_4")
def fetch_url_29_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_29_5")
def load_data_29_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_29_6")
def process_29_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_29_7")
def check_status_29_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_29_8")
def search_29_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_29_9")
def calculate_29_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
