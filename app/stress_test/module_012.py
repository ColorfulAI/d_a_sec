"""Stress test module 12 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request

ALLOWED_FETCH_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")

@app.route("/query_12_0")
def query_db_12_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    resp = make_response(escape(str(cursor.fetchall())))
    resp.content_type = "text/plain"
    return resp

@app.route("/cmd_12_1")
def run_cmd_12_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_12_2")
def read_file_12_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(SAFE_BASE_DIR):
        return "Access denied", 403
    with open(real_path, "r") as f:
        resp = make_response(escape(f.read()))
        resp.content_type = "text/plain"
        return resp

@app.route("/render_12_3")
def render_page_12_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_12_4")
def fetch_url_12_4():
    key = request.args.get("url")
    url = ALLOWED_FETCH_URLS.get(key)
    if url is None:
        return "URL not allowed", 404
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(url)
    return resp.read()

@app.route("/load_12_5")
def load_data_12_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_12_6")
def process_12_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_12_7")
def check_status_12_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_12_8")
def search_12_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_12_9")
def calculate_12_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
