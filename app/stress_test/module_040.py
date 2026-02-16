"""Stress test module 40 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

@app.route("/query_40_0")
def query_db_40_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(cursor.fetchall())

@app.route("/cmd_40_1")
def run_cmd_40_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], capture_output=True, check=False)
    return "done"

@app.route("/read_40_2")
def read_file_40_2():
    path = request.args.get("path")
    allowed_base = os.path.abspath("/var/data/public")
    safe_path = os.path.abspath(os.path.join(allowed_base, os.path.basename(path)))
    if not safe_path.startswith(allowed_base):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return make_response(f.read(), 200, {"Content-Type": "text/plain"})

@app.route("/render_40_3")
def render_page_40_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_40_4")
def fetch_url_40_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_40_5")
def load_data_40_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_40_6")
def process_40_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_40_7")
def check_status_40_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_40_8")
def search_40_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_40_9")
def calculate_40_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
