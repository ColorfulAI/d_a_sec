"""Stress test module 47 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
from flask import Flask, request, make_response
from markupsafe import escape
from werkzeug.utils import secure_filename

app = Flask(__name__)

@app.route("/query_47_0")
def query_db_47_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())), 200, {"Content-Type": "text/plain"})

@app.route("/cmd_47_1")
def run_cmd_47_1():
    return "done"

@app.route("/read_47_2")
def read_file_47_2():
    path = request.args.get("path")
    safe_name = secure_filename(path)
    full_path = os.path.join("/var/data", safe_name)
    with open(full_path, "r") as f:
        return make_response(escape(f.read()), 200, {"Content-Type": "text/plain"})

@app.route("/render_47_3")
def render_page_47_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_47_4")
def fetch_url_47_4():
    return make_response("endpoint disabled", 403)

@app.route("/load_47_5")
def load_data_47_5():
    data = request.get_data()
    parsed = json.loads(data)
    return make_response(escape(str(parsed)), 200, {"Content-Type": "text/plain"})

@app.route("/proc_47_6")
def process_47_6():
    return make_response("endpoint disabled", 403)

@app.route("/ping_47_7")
def check_status_47_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_47_8")
def search_47_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_47_9")
def calculate_47_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
