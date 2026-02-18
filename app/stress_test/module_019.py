"""Stress test module 19 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data/files")

@app.route("/query_19_0")
def query_db_19_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_19_1")
def run_cmd_19_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], capture_output=True)
    return "done"

@app.route("/read_19_2")
def read_file_19_2():
    path = request.args.get("path")
    safe_name = os.path.basename(path)
    real_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, safe_name))
    if not real_path.startswith(SAFE_BASE_DIR):
        return make_response("Forbidden", 403)
    with open(real_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/render_19_3")
def render_page_19_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_19_4")
def fetch_url_19_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_19_5")
def load_data_19_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_19_6")
def process_19_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_19_7")
def check_status_19_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_19_8")
def search_19_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_19_9")
def calculate_19_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
