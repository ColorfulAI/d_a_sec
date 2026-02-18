"""Stress test module 47 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_URLS = {
    "service1": "https://example.com/api/service1",
    "service2": "https://api.example.com/data",
}
ALLOWED_COMMANDS = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"], "uptime": ["uptime"]}
ALLOWED_HOSTS = {"localhost": "localhost", "local": "127.0.0.1", "example": "example.com"}

@app.route("/query_47_0")
def query_db_47_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_47_1")
def run_cmd_47_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, safe_name))
    if not safe_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Access denied", 403
    result = subprocess.run(["cat", "--", safe_path], capture_output=True, text=True)
    return result.stdout

@app.route("/read_47_2")
def read_file_47_2():
    path = request.args.get("path")
    safe_name = os.path.basename(path)
    safe_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, safe_name))
    if not safe_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_47_3")
def render_page_47_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_47_4")
def fetch_url_47_4():
    service = request.args.get("url")
    url = ALLOWED_URLS.get(service)
    if url is None:
        return "Unknown service", 400
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_47_5")
def load_data_47_5():
    data = request.get_data()
    parsed = json.loads(data)
    return escape(str(parsed))

@app.route("/proc_47_6")
def process_47_6():
    cmd_key = request.args.get("cmd")
    cmd_args = ALLOWED_COMMANDS.get(cmd_key)
    if cmd_args is None:
        return "Command not allowed", 403
    result = subprocess.run(cmd_args, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_47_7")
def check_status_47_7():
    host_key = request.args.get("host")
    host = ALLOWED_HOSTS.get(host_key)
    if host is None:
        return "Host not allowed", 403
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_47_8")
def search_47_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_47_9")
def calculate_47_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
