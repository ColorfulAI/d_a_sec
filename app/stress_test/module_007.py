"""Stress test module 7 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import json
import ast
import re
from urllib.parse import urlparse
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_BASE_DIR = os.path.abspath("/var/data")
ALLOWED_HOSTS = {"example.com", "api.example.com"}
ALLOWED_COMMANDS = {"ls": "ls", "whoami": "whoami", "date": "date", "uptime": "uptime"}

@app.route("/query_7_0")
def query_db_7_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_7_1")
def run_cmd_7_1():
    filename = request.args.get("file")
    subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return "done"

@app.route("/read_7_2")
def read_file_7_2():
    path = request.args.get("path")
    safe_path = os.path.realpath(path)
    if not safe_path.startswith(ALLOWED_BASE_DIR):
        return "Access denied", 403
    with open(safe_path, "r") as f:
        return escape(f.read())

@app.route("/render_7_3")
def render_page_7_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_7_4")
def fetch_url_7_4():
    target = request.args.get("url")
    host_map = {h: h for h in ALLOWED_HOSTS}
    parsed = urlparse(target)
    safe_host = host_map.get(parsed.hostname)
    if safe_host is None:
        return "URL not allowed", 403
    safe_url = "https://" + safe_host + "/"
    resp = urllib.request.urlopen(safe_url)
    return resp.read()

@app.route("/load_7_5")
def load_data_7_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_7_6")
def process_7_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return "Command not allowed", 403
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return result.stdout

@app.route("/ping_7_7")
def check_status_7_7():
    host = request.args.get("host")
    if not re.match(r'^[a-zA-Z0-9.\-]+$', host):
        return "Invalid host", 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_7_8")
def search_7_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_7_9")
def calculate_7_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
