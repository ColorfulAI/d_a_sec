"""Stress test module 9 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response, Response
from markupsafe import escape

app = Flask(__name__)

SAFE_DIR = "/var/app/data"

@app.route("/query_9_0")
def query_db_9_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return Response(str(cursor.fetchall()), content_type="text/plain")

@app.route("/cmd_9_1")
def run_cmd_9_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], capture_output=True)
    return "done"

@app.route("/read_9_2")
def read_file_9_2():
    key = request.args.get("path")
    FILE_MAP = {"readme": "readme.txt", "config": "config.txt", "data": "data.txt"}
    if key not in FILE_MAP:
        return "File not allowed", 403
    safe_path = os.path.join(SAFE_DIR, FILE_MAP[key])
    with open(safe_path, "r") as f:
        return Response(f.read(), content_type="text/plain")

@app.route("/render_9_3")
def render_page_9_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_9_4")
def fetch_url_9_4():
    key = request.args.get("url")
    URL_MAP = {"api": "https://example.com/api", "status": "https://example.com/status"}
    if key not in URL_MAP:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(URL_MAP[key])
    return resp.read()

@app.route("/load_9_5")
def load_data_9_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_9_6")
def process_9_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_9_7")
def check_status_9_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_9_8")
def search_9_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_9_9")
def calculate_9_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
