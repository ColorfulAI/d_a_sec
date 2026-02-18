"""Stress test module 36 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import urllib.request
from markupsafe import escape
from flask import Flask, request, make_response, abort

app = Flask(__name__)

@app.route("/query_36_0")
def query_db_36_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_36_1")
def run_cmd_36_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

ALLOWED_FILES = {"readme": "/var/data/readme.txt", "config": "/var/data/config.txt"}

@app.route("/read_36_2")
def read_file_36_2():
    file_key = request.args.get("path")
    if file_key not in ALLOWED_FILES:
        abort(403)
    with open(ALLOWED_FILES[file_key], "r") as f:
        content = f.read()
    return make_response(escape(content))

@app.route("/render_36_3")
def render_page_36_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

ALLOWED_URLS = {"example": "https://example.com", "api": "https://api.example.com"}

@app.route("/fetch_36_4")
def fetch_url_36_4():
    url_key = request.args.get("url")
    if url_key not in ALLOWED_URLS:
        abort(403)
    resp = urllib.request.urlopen(ALLOWED_URLS[url_key])
    return resp.read()

@app.route("/load_36_5")
def load_data_36_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))))

ALLOWED_COMMANDS = {"ls": ["ls"], "date": ["date"], "whoami": ["whoami"], "uptime": ["uptime"]}

@app.route("/proc_36_6")
def process_36_6():
    cmd = request.args.get("cmd")
    if cmd not in ALLOWED_COMMANDS:
        abort(403)
    result = subprocess.run(ALLOWED_COMMANDS[cmd], capture_output=True)
    return result.stdout

@app.route("/ping_36_7")
def check_status_36_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_36_8")
def search_36_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_36_9")
def calculate_36_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
