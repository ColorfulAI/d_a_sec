"""Stress test module 30 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_URLS = {
    "service1": "https://api.example.com/data",
    "service2": "https://api.example.com/status",
}

@app.route("/query_30_0")
def query_db_30_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_30_1")
def run_cmd_30_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True)
    return result.stdout

ALLOWED_FILES = {
    "readme": "/var/data/readme.txt",
    "config": "/var/data/config.txt",
    "data": "/var/data/data.csv",
}


@app.route("/read_30_2")
def read_file_30_2():
    file_key = request.args.get("path")
    if file_key not in ALLOWED_FILES:
        return "File not allowed", 403
    with open(ALLOWED_FILES[file_key], "r") as f:
        return escape(f.read())

@app.route("/render_30_3")
def render_page_30_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_30_4")
def fetch_url_30_4():
    url_key = request.args.get("url")
    if url_key not in ALLOWED_URLS:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(ALLOWED_URLS[url_key])
    return resp.read()

@app.route("/load_30_5")
def load_data_30_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_30_6")
def process_30_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_30_7")
def check_status_30_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_30_8")
def search_30_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_30_9")
def calculate_30_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
