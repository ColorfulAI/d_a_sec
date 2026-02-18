"""Stress test module 4 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_DIR = os.path.realpath("/var/data")

@app.route("/query_4_0")
def query_db_4_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_4_1")
def run_cmd_4_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_4_2")
def read_file_4_2():
    path = request.args.get("path")
    real_path = os.path.realpath(os.path.join(SAFE_DIR, path))
    if not real_path.startswith(SAFE_DIR + os.sep):
        return "Forbidden", 403
    with open(real_path, "r") as f:
        return str(escape(f.read()))

@app.route("/render_4_3")
def render_page_4_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_4_4")
def fetch_url_4_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_4_5")
def load_data_4_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_4_6")
def process_4_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_4_7")
def check_status_4_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_4_8")
def search_4_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_4_9")
def calculate_4_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
