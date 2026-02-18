"""Stress test module 4 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_DIR = os.path.realpath("/var/data")
ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}
ALLOWED_CMDS = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"]}

@app.route("/query_4_0")
def query_db_4_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return str(escape(str(cursor.fetchall())))

@app.route("/cmd_4_1")
def run_cmd_4_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_4_2")
def read_file_4_2():
    path = request.args.get("path")
    real_path = os.path.realpath(os.path.join(SAFE_DIR, path))
    if not real_path.startswith(SAFE_DIR + os.sep):
        return "Forbidden", 403
    with open(real_path, "r") as f:
        return str(escape(f.read()))

@app.route("/render_4_3")
def render_page_4_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_4_4")
def fetch_url_4_4():
    url_key = request.args.get("url")
    safe_url = ALLOWED_URLS.get(url_key)
    if safe_url is None:
        return "Forbidden", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_4_5")
def load_data_4_5():
    data = request.get_data()
    return str(escape(str(json.loads(data))))

@app.route("/proc_4_6")
def process_4_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_CMDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run(safe_cmd, capture_output=True)
    return result.stdout

@app.route("/ping_4_7")
def check_status_4_7():
    host = request.args.get("host")
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_4_8")
def search_4_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(escape(str(cursor.fetchall())))

@app.route("/calc_4_9")
def calculate_4_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
