"""Stress test module 3 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data/public")

ALLOWED_FILES = {
    "readme": "readme.txt",
    "config": "config.txt",
    "data": "data.csv",
}

@app.route("/query_3_0")
def query_db_3_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_3_1")
def run_cmd_3_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    safe_path = os.path.join(SAFE_BASE_DIR, safe_name)
    result = subprocess.run(["cat", safe_path], capture_output=True, check=False)
    return result.stdout.decode()

@app.route("/read_3_2")
def read_file_3_2():
    file_key = request.args.get("path")
    filename = ALLOWED_FILES.get(file_key)
    if filename is None:
        return "Not found", 404
    with open(os.path.join(SAFE_BASE_DIR, filename), "r") as f:
        return escape(f.read())

@app.route("/render_3_3")
def render_page_3_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_3_4")
def fetch_url_3_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_3_5")
def load_data_3_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_3_6")
def process_3_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_3_7")
def check_status_3_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_3_8")
def search_3_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_3_9")
def calculate_3_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
