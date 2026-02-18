"""Stress test module 16 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import html
import urllib.request
from urllib.parse import urlparse
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_HOSTS = {"127.0.0.1": "127.0.0.1", "localhost": "localhost"}
SAFE_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_COMMANDS = {"ls": "ls", "date": "date", "whoami": "whoami", "uptime": "uptime"}

@app.route("/query_16_0")
def query_db_16_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(html.escape(str(cursor.fetchall())), 200, {"Content-Type": "text/plain"})

@app.route("/cmd_16_1")
def run_cmd_16_1():
    filename = request.args.get("file")
    safe_path = os.path.realpath(filename)
    if not safe_path.startswith(SAFE_BASE_DIR + os.sep) and safe_path != SAFE_BASE_DIR:
        return make_response("Forbidden", 403)
    subprocess.run(["cat", safe_path], capture_output=True, check=False)
    return "done"

@app.route("/read_16_2")
def read_file_16_2():
    path = request.args.get("path")
    available = {f: f for f in os.listdir(SAFE_BASE_DIR) if os.path.isfile(os.path.join(SAFE_BASE_DIR, f))}
    safe_name = available.get(os.path.basename(path))
    if safe_name is None:
        return make_response("Forbidden", 403)
    with open(os.path.join(SAFE_BASE_DIR, safe_name), "r") as f:
        return make_response(html.escape(f.read()), 200, {"Content-Type": "text/plain"})

@app.route("/render_16_3")
def render_page_16_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_16_4")
def fetch_url_16_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_16_5")
def load_data_16_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_16_6")
def process_16_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_16_7")
def check_status_16_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_16_8")
def search_16_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_16_9")
def calculate_16_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
