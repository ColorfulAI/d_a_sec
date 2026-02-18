"""Stress test module 39 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response, Response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("/var/data/public")

@app.route("/query_39_0")
def query_db_39_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return Response(str(cursor.fetchall()), content_type="text/plain")

@app.route("/cmd_39_1")
def run_cmd_39_1():
    filename = request.args.get("file")
    if not filename or not all(c.isalnum() or c in "._-" for c in filename):
        return "Invalid filename", 400
    subprocess.run(["cat", filename], capture_output=True, check=False)
    return "done"

@app.route("/read_39_2")
def read_file_39_2():
    path = request.args.get("path")
    safe_path = os.path.normpath(os.path.join(SAFE_BASE_DIR, path))
    if not safe_path.startswith(SAFE_BASE_DIR):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        content = f.read()
    return Response(content, content_type="text/plain")

@app.route("/render_39_3")
def render_page_39_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_39_4")
def fetch_url_39_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_39_5")
def load_data_39_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_39_6")
def process_39_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_39_7")
def check_status_39_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_39_8")
def search_39_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_39_9")
def calculate_39_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
