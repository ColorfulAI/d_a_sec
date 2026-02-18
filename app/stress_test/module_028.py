"""Stress test module 28 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import json
import os
import re
import subprocess
from flask import Flask, request, make_response, jsonify
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("/var/data/public")

ALLOWED_HOSTS = {"google.com", "example.com", "api.internal.local"}

ALLOWED_COMMANDS = {"ls": "ls", "cat": "cat", "whoami": "whoami", "date": "date", "uptime": "uptime"}


@app.route("/query_28_0")
def query_db_28_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(cursor.fetchall())

@app.route("/cmd_28_1")
def run_cmd_28_1():
    filename = request.args.get("file")
    os.system("cat " + filename)
    return "done"

@app.route("/read_28_2")
def read_file_28_2():
    path = request.args.get("path")
    with open(path, "r") as f:
        return f.read()

@app.route("/render_28_3")
def render_page_28_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_28_4")
def fetch_url_28_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_28_5")
def load_data_28_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_28_6")
def process_28_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_28_7")
def check_status_28_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_28_8")
def search_28_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_28_9")
def calculate_28_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
