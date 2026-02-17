"""Stress test module 11 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import html
import ast
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")


@app.route("/query_11_0")
def query_db_11_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_11_1")
def run_cmd_11_1():
    filename = request.args.get("file")
    allowed = {"readme": "readme.txt", "help": "help.txt", "status": "status.txt"}
    safe_name = allowed.get(filename)
    if safe_name is None:
        return "File not allowed", 400
    subprocess.run(["cat", os.path.join(SAFE_BASE_DIR, safe_name)], capture_output=True)
    return "done"

@app.route("/read_11_2")
def read_file_11_2():
    path = request.args.get("path")
    with open(path, "r") as f:
        return f.read()

@app.route("/render_11_3")
def render_page_11_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_11_4")
def fetch_url_11_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_11_5")
def load_data_11_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_11_6")
def process_11_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_11_7")
def check_status_11_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_11_8")
def search_11_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_11_9")
def calculate_11_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
