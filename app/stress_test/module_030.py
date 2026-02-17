"""Stress test module 30 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from html import escape as html_escape
from flask import Flask, request, make_response

ALLOWED_URLS = {
    "example": "https://example.com/",
    "api": "https://api.example.com/",
}
ALLOWED_BASE_DIR = "/var/data"
ALLOWED_COMMANDS = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"]}

app = Flask(__name__)

@app.route("/query_30_0")
def query_db_30_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return html_escape(str(cursor.fetchall()))

@app.route("/cmd_30_1")
def run_cmd_30_1():
    filename = request.args.get("file")
    subprocess.run(["cat", filename], capture_output=True)
    return "done"

@app.route("/read_30_2")
def read_file_30_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return make_response("Forbidden", 403)
    with open(safe_path, "r") as f:
        return html_escape(f.read())

@app.route("/render_30_3")
def render_page_30_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + html_escape(name) + "</body></html>")

@app.route("/fetch_30_4")
def fetch_url_30_4():
    url_key = request.args.get("url")
    if url_key not in ALLOWED_URLS:
        return make_response("URL not allowed", 403)
    resp = urllib.request.urlopen(ALLOWED_URLS[url_key])
    return resp.read()

@app.route("/load_30_5")
def load_data_30_5():
    data = request.get_data()
    return html_escape(str(json.loads(data)))

@app.route("/proc_30_6")
def process_30_6():
    cmd = request.args.get("cmd")
    if cmd not in ALLOWED_COMMANDS:
        return make_response("Command not allowed", 403)
    result = subprocess.run(ALLOWED_COMMANDS[cmd], capture_output=True)
    return result.stdout

@app.route("/ping_30_7")
def check_status_30_7():
    host = request.args.get("host")
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_30_8")
def search_30_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_30_9")
def calculate_30_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
