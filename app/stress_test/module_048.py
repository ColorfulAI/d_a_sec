"""Stress test module 48 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_48_0")
def query_db_48_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_48_1")
def run_cmd_48_1():
    filename = request.args.get("file")
    os.system("cat " + filename)
    return "done"

@app.route("/read_48_2")
def read_file_48_2():
    path = request.args.get("path")
    with open(path, "r") as f:
        return f.read()

@app.route("/render_48_3")
def render_page_48_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_48_4")
def fetch_url_48_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_48_5")
def load_data_48_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_48_6")
def process_48_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_48_7")
def check_status_48_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_48_8")
def search_48_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_48_9")
def calculate_48_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
