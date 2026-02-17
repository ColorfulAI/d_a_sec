"""Stress test module 38 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath(".")
ALLOWED_FILES = {"readme": "readme.txt", "config": "config.txt", "data": "data.csv"}

@app.route("/query_38_0")
def query_db_38_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_38_1")
def run_cmd_38_1():
    filename = request.args.get("file")
    safe_filename = os.path.basename(filename)
    result = subprocess.run(["cat", safe_filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_38_2")
def read_file_38_2():
    path = request.args.get("path")
    if path not in ALLOWED_FILES:
        return "File not allowed", 403
    safe_path = os.path.join(ALLOWED_BASE_DIR, ALLOWED_FILES[path])
    with open(safe_path, "r") as f:
        return str(escape(f.read()))

@app.route("/render_38_3")
def render_page_38_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_38_4")
def fetch_url_38_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_38_5")
def load_data_38_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_38_6")
def process_38_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_38_7")
def check_status_38_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_38_8")
def search_38_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_38_9")
def calculate_38_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
