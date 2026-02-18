"""Stress test module 24 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import re
import urllib.request
from flask import Flask, request, make_response, Response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")

@app.route("/query_24_0")
def query_db_24_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return Response(str(cursor.fetchall()), content_type="text/plain")

@app.route("/cmd_24_1")
def run_cmd_24_1():
    filename = request.args.get("file")
    if not filename or not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        return Response("Invalid filename", status=400, content_type="text/plain")
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return Response(result.stdout, content_type="text/plain")

@app.route("/read_24_2")
def read_file_24_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(SAFE_BASE_DIR):
        return Response("Access denied", status=403, content_type="text/plain")
    with open(real_path, "r") as f:
        return Response(f.read(), content_type="text/plain")

@app.route("/render_24_3")
def render_page_24_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_24_4")
def fetch_url_24_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_24_5")
def load_data_24_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_24_6")
def process_24_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_24_7")
def check_status_24_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_24_8")
def search_24_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_24_9")
def calculate_24_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
