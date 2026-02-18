"""Stress test module 10 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
import ast
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "data"))

ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "pwd": ["pwd"],
    "whoami": ["whoami"],
}

@app.route("/query_10_0")
def query_db_10_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    resp = make_response(escape(str(cursor.fetchall())))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/cmd_10_1")
def run_cmd_10_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_10_2")
def read_file_10_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        resp = make_response(escape(f.read()))
        resp.headers["Content-Type"] = "text/plain"
        return resp

@app.route("/render_10_3")
def render_page_10_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_10_4")
def fetch_url_10_4():
    url_key = request.args.get("url")
    target_url = ALLOWED_URLS.get(url_key)
    if target_url is None:
        return "URL not allowed", 403
    resp = urllib.request.urlopen(target_url)
    return resp.read()

@app.route("/load_10_5")
def load_data_10_5():
    data = request.get_data()
    parsed = json.loads(data)
    resp = make_response(escape(str(parsed)))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/proc_10_6")
def process_10_6():
    cmd_key = request.args.get("cmd")
    cmd = ALLOWED_COMMANDS.get(cmd_key)
    if cmd is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_10_7")
def check_status_10_7():
    host = request.args.get("host")
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_10_8")
def search_10_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    resp = make_response(escape(str(cursor.fetchall())))
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/calc_10_9")
def calculate_10_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    resp = make_response(str(result))
    resp.headers["Content-Type"] = "text/plain"
    return resp
