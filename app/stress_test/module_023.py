"""Stress test module 23 — intentional vulnerabilities for CodeQL testing."""
import ast
import json
import os
import sqlite3
import subprocess
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.realpath("/var/data")
ALLOWED_URLS = {
    "status": "https://api.example.com/status",
    "health": "https://api.example.com/health",
}
ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}
ALLOWED_PING_HOSTS = {"google": "google.com", "dns": "8.8.8.8", "local": "localhost"}

@app.route("/query_23_0")
def query_db_23_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    resp = make_response(escape(str(cursor.fetchall())))
    resp.content_type = "text/plain"
    return resp

@app.route("/cmd_23_1")
def run_cmd_23_1():
    filename = request.args.get("file")
    safe_filename = os.path.basename(filename)
    result = subprocess.run(["cat", "--", safe_filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_23_2")
def read_file_23_2():
    path = request.args.get("path")
    safe_name = os.path.basename(path)
    real_path = os.path.realpath(os.path.join(ALLOWED_BASE_DIR, safe_name))
    if not real_path.startswith(ALLOWED_BASE_DIR + os.sep):
        return "Forbidden", 403
    with open(real_path, "r") as f:
        resp = make_response(escape(f.read()))
        resp.content_type = "text/plain"
        return resp

@app.route("/render_23_3")
def render_page_23_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_23_4")
def fetch_url_23_4():
    url_key = request.args.get("url")
    safe_url = ALLOWED_URLS.get(url_key)
    if safe_url is None:
        return "Forbidden", 403
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_23_5")
def load_data_23_5():
    data = request.get_data()
    parsed = json.loads(data)
    resp = make_response(escape(str(parsed)))
    resp.content_type = "text/plain"
    return resp

@app.route("/proc_23_6")
def process_23_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Forbidden", 403
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_23_7")
def check_status_23_7():
    host_key = request.args.get("host")
    host = ALLOWED_PING_HOSTS.get(host_key)
    if host is None:
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_23_8")
def search_23_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    resp = make_response(escape(str(cursor.fetchall())))
    resp.content_type = "text/plain"
    return resp

@app.route("/calc_23_9")
def calculate_23_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
