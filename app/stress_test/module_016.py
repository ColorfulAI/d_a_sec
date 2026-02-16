"""Stress test module 16 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

@app.route("/query_16_0")
def query_db_16_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = '" + user_id + "'")
    return str(cursor.fetchall())

@app.route("/cmd_16_1")
def run_cmd_16_1():
    filename = request.args.get("file")
    os.system("cat " + filename)
    return "done"

@app.route("/read_16_2")
def read_file_16_2():
    path = request.args.get("path")
    with open(path, "r") as f:
        return f.read()

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
