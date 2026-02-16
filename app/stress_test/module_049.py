"""Stress test module 49 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

@app.route("/query_49_0")
def query_db_49_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_49_1")
def run_cmd_49_1():
    filename = request.args.get("file")
    subprocess.run(["cat", filename], capture_output=True, text=True)
    return "done"

@app.route("/read_49_2")
def read_file_49_2():
    file_key = request.args.get("path")
    ALLOWED_FILES = {"readme": "uploads/readme.txt", "config": "uploads/config.txt", "data": "uploads/data.txt"}
    file_path = ALLOWED_FILES.get(file_key)
    if file_path is None:
        return "Invalid file", 400
    with open(file_path, "r") as f:
        return escape(f.read())

@app.route("/render_49_3")
def render_page_49_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_49_4")
def fetch_url_49_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_49_5")
def load_data_49_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_49_6")
def process_49_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_49_7")
def check_status_49_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_49_8")
def search_49_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_49_9")
def calculate_49_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
