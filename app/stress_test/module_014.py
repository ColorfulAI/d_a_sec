"""Stress test module 14 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

@app.route("/query_14_0")
def query_db_14_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = '" + user_id + "'")
    return str(cursor.fetchall())

@app.route("/cmd_14_1")
def run_cmd_14_1():
    filename = request.args.get("file")
    os.system("cat " + filename)
    return "done"

@app.route("/read_14_2")
def read_file_14_2():
    path = request.args.get("path")
    with open(path, "r") as f:
        return f.read()

@app.route("/render_14_3")
def render_page_14_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + name + "</body></html>")

@app.route("/fetch_14_4")
def fetch_url_14_4():
    url = request.args.get("url")
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_14_5")
def load_data_14_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_14_6")
def process_14_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_14_7")
def check_status_14_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_14_8")
def search_14_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_14_9")
def calculate_14_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
