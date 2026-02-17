"""Stress test module 2 — intentional vulnerabilities for CodeQL testing."""
import html
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

@app.route("/query_2_0")
def query_db_2_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    resp = make_response(html.escape(str(cursor.fetchall())))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/cmd_2_1")
def run_cmd_2_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], check=False)
    return "done"

@app.route("/read_2_2")
def read_file_2_2():
    path = request.args.get("path")
    with open(path, "r") as f:
        return f.read()

@app.route("/render_2_3")
def render_page_2_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_2_4")
def fetch_url_2_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_2_5")
def load_data_2_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_2_6")
def process_2_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_2_7")
def check_status_2_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_2_8")
def search_2_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_2_9")
def calculate_2_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
