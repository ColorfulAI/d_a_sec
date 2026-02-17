"""Stress test module 23 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import html
import json
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data/files")
ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}
ALLOWED_CMDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}

@app.route("/query_23_0")
def query_db_23_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_23_1")
def run_cmd_23_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    safe_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, safe_name))
    if not safe_path.startswith(SAFE_BASE_DIR + os.sep):
        return "Forbidden", 403
    if not os.path.isfile(safe_path):
        return "File not found", 404
    with open(safe_path, "r") as f:
        _ = f.read()
    return "done"

@app.route("/read_23_2")
def read_file_23_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, os.path.basename(path)))
    if not safe_path.startswith(SAFE_BASE_DIR + os.sep):
        return "Forbidden", 403
    with open(safe_path, "r") as f:
        return html.escape(f.read())

@app.route("/render_23_3")
def render_page_23_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_23_4")
def fetch_url_23_4():
    url_key = request.args.get("url")
    url = ALLOWED_URLS.get(url_key)
    if url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_23_5")
def load_data_23_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))

@app.route("/proc_23_6")
def process_23_6():
    cmd_name = request.args.get("cmd")
    cmd_list = ALLOWED_CMDS.get(cmd_name)
    if cmd_list is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd_list, capture_output=True)
    return result.stdout

@app.route("/ping_23_7")
def check_status_23_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_23_8")
def search_23_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_23_9")
def calculate_23_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
