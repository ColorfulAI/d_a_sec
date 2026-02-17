"""Stress test module 24 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response, jsonify
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.abspath("/var/data/public")
ALLOWED_FILES = {
    "readme": "readme.txt",
    "config": "config.txt",
    "data": "data.csv",
}
ALLOWED_URLS = {
    "example": "https://example.com",
    "test": "https://test.example.com",
}

@app.route("/query_24_0")
def query_db_24_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify(cursor.fetchall())

@app.route("/cmd_24_1")
def run_cmd_24_1():
    file_key = request.args.get("file")
    if file_key not in ALLOWED_FILES:
        return "File not allowed", 403
    safe_path = os.path.join(SAFE_BASE_DIR, ALLOWED_FILES[file_key])
    with open(safe_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/read_24_2")
def read_file_24_2():
    file_key = request.args.get("path")
    if file_key not in ALLOWED_FILES:
        return "File not allowed", 403
    safe_path = os.path.join(SAFE_BASE_DIR, ALLOWED_FILES[file_key])
    with open(safe_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/render_24_3")
def render_page_24_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_24_4")
def fetch_url_24_4():
    target = request.args.get("url")
    if target not in ALLOWED_URLS:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(ALLOWED_URLS[target])
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
