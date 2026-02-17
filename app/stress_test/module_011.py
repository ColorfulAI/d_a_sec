"""Stress test module 11 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import html
import ast
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")


@app.route("/query_11_0")
def query_db_11_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html.escape(str(cursor.fetchall()))

@app.route("/cmd_11_1")
def run_cmd_11_1():
    filename = request.args.get("file")
    allowed = {"readme": "readme.txt", "help": "help.txt", "status": "status.txt"}
    safe_name = allowed.get(filename)
    if safe_name is None:
        return "File not allowed", 400
    subprocess.run(["cat", os.path.join(SAFE_BASE_DIR, safe_name)], capture_output=True)
    return "done"

@app.route("/read_11_2")
def read_file_11_2():
    path_key = request.args.get("path")
    allowed_paths = {"config": "/var/data/config.txt", "readme": "/var/data/readme.txt"}
    safe_path = allowed_paths.get(path_key)
    if safe_path is None:
        return "Path not allowed", 400
    with open(safe_path, "r") as f:
        resp = make_response(html.escape(f.read()))
        resp.headers["Content-Type"] = "text/plain"
        return resp

@app.route("/render_11_3")
def render_page_11_3():
    name = request.args.get("name")
    safe_name = html.escape(name)
    return make_response("<html><body>Hello " + safe_name + "</body></html>")

@app.route("/fetch_11_4")
def fetch_url_11_4():
    url_key = request.args.get("url")
    allowed_urls = {"example": "https://example.com", "api": "https://api.example.com"}
    url = allowed_urls.get(url_key)
    if url is None:
        return "URL not allowed", 400
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_11_5")
def load_data_11_5():
    data = request.get_data()
    return html.escape(str(json.loads(data)))

@app.route("/proc_11_6")
def process_11_6():
    cmd_key = request.args.get("cmd")
    allowed_cmds = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"]}
    cmd_list = allowed_cmds.get(cmd_key)
    if cmd_list is None:
        return "Command not allowed", 400
    result = subprocess.run(cmd_list, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_11_7")
def check_status_11_7():
    host_key = request.args.get("host")
    allowed_hosts = {"localhost": "127.0.0.1", "google": "google.com"}
    host = allowed_hosts.get(host_key)
    if host is None:
        return "Host not allowed", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_11_8")
def search_11_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return html.escape(str(cursor.fetchall()))

@app.route("/calc_11_9")
def calculate_11_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
