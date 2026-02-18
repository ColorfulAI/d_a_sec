"""Stress test module 0 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_0_0")
def query_db_0_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

ALLOWED_CMD_FILES = {
    "readme": "/var/app/data/readme.txt",
    "config": "/var/app/data/config.txt",
    "log": "/var/app/data/app.log",
}


@app.route("/cmd_0_1")
def run_cmd_0_1():
    key = request.args.get("file")
    filepath = ALLOWED_CMD_FILES.get(key)
    if filepath is None:
        return "File not allowed", 403
    try:
        with open(filepath, "r") as f:
            return make_response(escape(f.read()))
    except (FileNotFoundError, IsADirectoryError):
        return "File not found", 404

ALLOWED_READ_FILES = {
    "readme": "/var/app/data/readme.txt",
    "config": "/var/app/data/config.txt",
    "log": "/var/app/data/app.log",
}


@app.route("/read_0_2")
def read_file_0_2():
    key = request.args.get("path")
    filepath = ALLOWED_READ_FILES.get(key)
    if filepath is None:
        return "File not allowed", 403
    with open(filepath, "r") as f:
        content = f.read()
    return make_response(escape(content))

@app.route("/render_0_3")
def render_page_0_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

ALLOWED_URLS = {"api": "https://example.com/api", "data": "https://api.example.com/data"}


@app.route("/fetch_0_4")
def fetch_url_0_4():
    key = request.args.get("url")
    url = ALLOWED_URLS.get(key)
    if url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_0_5")
def load_data_0_5():
    data = request.get_data()
    return make_response(escape(str(json.loads(data))))

@app.route("/proc_0_6")
def process_0_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_0_7")
def check_status_0_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_0_8")
def search_0_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_0_9")
def calculate_0_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
