"""Stress test module 17 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_17_0")
def query_db_17_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_17_1")
def run_cmd_17_1():
    filename = request.args.get("file")
    os.system("cat " + filename)
    return "done"

@app.route("/read_17_2")
def read_file_17_2():
    path = request.args.get("path")
    with open(path, "r") as f:
        return f.read()

@app.route("/render_17_3")
def render_page_17_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_17_4")
def fetch_url_17_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_17_5")
def load_data_17_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_17_6")
def process_17_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_17_7")
def check_status_17_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_17_8")
def search_17_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_17_9")
def calculate_17_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
