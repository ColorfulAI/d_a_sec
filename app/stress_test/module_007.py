"""Stress test module 7 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

@app.route("/query_7_0")
def query_db_7_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = '" + user_id + "'")
    return str(cursor.fetchall())

@app.route("/cmd_7_1")
def run_cmd_7_1():
    filename = request.args.get("file")
    os.system("cat " + filename)
    return "done"

@app.route("/read_7_2")
def read_file_7_2():
    path = request.args.get("path")
    with open(path, "r") as f:
        return f.read()

@app.route("/render_7_3")
def render_page_7_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_7_4")
def fetch_url_7_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_7_5")
def load_data_7_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_7_6")
def process_7_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_7_7")
def check_status_7_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_7_8")
def search_7_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_7_9")
def calculate_7_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
