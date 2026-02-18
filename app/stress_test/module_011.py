"""Stress test module 11 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from urllib.parse import urlparse
from flask import Flask, request, make_response, Response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")

ALLOWED_HOSTS = {"example.com", "api.example.com"}

@app.route("/query_11_0")
def query_db_11_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return Response(str(cursor.fetchall()), content_type="text/plain")

@app.route("/cmd_11_1")
def run_cmd_11_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True)
    return Response(result.stdout, content_type="text/plain")

@app.route("/read_11_2")
def read_file_11_2():
    path = request.args.get("path")
    real_path = os.path.realpath(path)
    if not real_path.startswith(SAFE_BASE_DIR):
        return Response("Access denied", status=403, content_type="text/plain")
    with open(real_path, "r") as f:
        return Response(f.read(), content_type="text/plain")

@app.route("/render_11_3")
def render_page_11_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_11_4")
def fetch_url_11_4():
    url = request.args.get("url")
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return Response("Host not allowed", status=400, content_type="text/plain")
    safe_url = parsed.scheme + "://" + parsed.hostname + parsed.path
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(safe_url)
    return resp.read()

@app.route("/load_11_5")
def load_data_11_5():
    data = request.get_data()
    return Response(str(json.loads(data)), content_type="text/plain")

@app.route("/proc_11_6")
def process_11_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_11_7")
def check_status_11_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_11_8")
def search_11_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_11_9")
def calculate_11_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
