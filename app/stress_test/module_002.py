"""Stress test module 2 — intentional vulnerabilities for CodeQL testing."""
import html
import re
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response

app = Flask(__name__)

ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}
SAFE_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_CMDS = {
    "ls": "ls",
    "whoami": "whoami",
    "date": "date",
    "uptime": "uptime",
}

@app.route("/query_2_0")
def query_db_2_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    resp = make_response(html.escape(str(cursor.fetchall())))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/cmd_2_1")
def run_cmd_2_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], check=False)
    return "done"

@app.route("/read_2_2")
def read_file_2_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(SAFE_BASE_DIR + os.sep):
        return make_response("Forbidden", 403)
    with open(real_path, "r") as f:
        resp = make_response(html.escape(f.read()))
        resp.headers["Content-Type"] = "text/plain"
        return resp

@app.route("/render_2_3")
def render_page_2_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html.escape(name) + "</body></html>")

@app.route("/fetch_2_4")
def fetch_url_2_4():
    url_key = request.args.get("url")
    target_url = ALLOWED_URLS.get(url_key)
    if target_url is None:
        return make_response("URL not allowed", 403)
    resp = urllib.request.urlopen(target_url)
    return resp.read()

@app.route("/load_2_5")
def load_data_2_5():
    data = request.get_data()
    resp = make_response(html.escape(str(json.loads(data))))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/proc_2_6")
def process_2_6():
    cmd = request.args.get("cmd")
    actual_cmd = ALLOWED_CMDS.get(cmd)
    if actual_cmd is None:
        return make_response("Command not allowed", 403)
    result = subprocess.run([actual_cmd], capture_output=True)
    return result.stdout

@app.route("/ping_2_7")
def check_status_2_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return make_response("Invalid host", 400)
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_2_8")
def search_2_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    resp = make_response(html.escape(str(cursor.fetchall())))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/calc_2_9")
def calculate_2_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
