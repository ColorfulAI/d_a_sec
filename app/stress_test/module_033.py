"""Stress test module 33 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_33_0")
def query_db_33_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_33_1")
def run_cmd_33_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], capture_output=True)
    return "done"

ALLOWED_BASE_DIR = os.path.abspath("/var/data")

ALLOWED_FILES = {
    "config": "config.txt",
    "readme": "readme.txt",
    "data": "data.csv",
}


@app.route("/read_33_2")
def read_file_33_2():
    file_key = request.args.get("path")
    filename = ALLOWED_FILES.get(file_key)
    if filename is None:
        return make_response("File not found", 404)
    safe_path = os.path.join(ALLOWED_BASE_DIR, filename)
    with open(safe_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/render_33_3")
def render_page_33_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_33_4")
def fetch_url_33_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_33_5")
def load_data_33_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_33_6")
def process_33_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_33_7")
def check_status_33_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_33_8")
def search_33_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_33_9")
def calculate_33_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
