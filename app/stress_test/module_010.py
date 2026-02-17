"""Stress test module 10 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response, Response
from markupsafe import escape

app = Flask(__name__)

@app.route("/query_10_0")
def query_db_10_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return Response(escape(str(cursor.fetchall())), content_type="text/plain")

@app.route("/cmd_10_1")
def run_cmd_10_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", "--", filename], capture_output=True, text=True)
    return Response(result.stdout, content_type="text/plain")

@app.route("/read_10_2")
def read_file_10_2():
    path = request.args.get("path")
    safe_base = os.path.realpath(os.path.join(os.path.dirname(__file__), "data"))
    real_path = os.path.normpath(os.path.join(safe_base, path))
    if not real_path.startswith(safe_base):
        return Response("Access denied", status=403, content_type="text/plain")
    with open(real_path, "r") as f:
        return Response(escape(f.read()), content_type="text/plain")

@app.route("/render_10_3")
def render_page_10_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_10_4")
def fetch_url_10_4():
    ALLOWED_URLS = {
        "example": "https://example.com/",
        "api": "https://api.example.com/",
    }
    url_key = request.args.get("url")
    url = ALLOWED_URLS.get(url_key)
    if url is None:
        return Response("URL not allowed", status=403, content_type="text/plain")
    resp = urllib.request.urlopen(url)
    return Response(resp.read(), content_type="text/plain")

@app.route("/load_10_5")
def load_data_10_5():
    data = request.get_data()
    return Response(escape(str(json.loads(data))), content_type="text/plain")

@app.route("/proc_10_6")
def process_10_6():
    ALLOWED_COMMANDS = {
        "ls": ["ls"],
        "date": ["date"],
        "whoami": ["whoami"],
    }
    cmd_key = request.args.get("cmd")
    cmd_args = ALLOWED_COMMANDS.get(cmd_key)
    if cmd_args is None:
        return Response("Command not allowed", status=403, content_type="text/plain")
    result = subprocess.run(cmd_args, capture_output=True)
    return Response(result.stdout, content_type="text/plain")

@app.route("/ping_10_7")
def check_status_10_7():
    ALLOWED_HOSTS = {
        "google": "google.com",
        "example": "example.com",
        "localhost": "127.0.0.1",
    }
    host_key = request.args.get("host")
    host = ALLOWED_HOSTS.get(host_key)
    if host is None:
        return Response("Host not allowed", status=403, content_type="text/plain")
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return Response(result.stdout, content_type="text/plain")

@app.route("/search_10_8")
def search_10_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_10_9")
def calculate_10_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
