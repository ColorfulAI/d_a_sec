"""Stress test module 14 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import urllib.request
from flask import Flask, request, make_response, Response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data")

ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}

ALLOWED_PING_HOSTS = {
    "localhost": "127.0.0.1",
    "gateway": "192.168.1.1",
}

ALLOWED_FETCH_URLS = {
    "example": "https://example.com",
    "status": "https://status.example.com",
}

ALLOWED_FILES = {
    "report": os.path.join(SAFE_BASE_DIR, "report.txt"),
    "log": os.path.join(SAFE_BASE_DIR, "log.txt"),
    "config": os.path.join(SAFE_BASE_DIR, "config.txt"),
}


@app.route("/query_14_0")
def query_db_14_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return Response(str(cursor.fetchall()), content_type="text/plain")

@app.route("/cmd_14_1")
def run_cmd_14_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", "--", safe_name], check=False)
    return "done"

@app.route("/read_14_2")
def read_file_14_2():
    key = request.args.get("path")
    safe_path = ALLOWED_FILES.get(key)
    if safe_path is None:
        return Response("File not found", status=404, content_type="text/plain")
    with open(safe_path, "r") as f:
        return Response(f.read(), content_type="text/plain")

@app.route("/render_14_3")
def render_page_14_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_14_4")
def fetch_url_14_4():
    key = request.args.get("url")
    target = ALLOWED_FETCH_URLS.get(key)
    if target is None:
        return Response("URL not allowed", status=403, content_type="text/plain")
    resp = urllib.request.urlopen(target)
    return resp.read()

@app.route("/load_14_5")
def load_data_14_5():
    data = request.get_data()
    return Response(str(json.loads(data)), content_type="text/plain")

@app.route("/proc_14_6")
def process_14_6():
    cmd = request.args.get("cmd")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return Response("Command not allowed", status=403, content_type="text/plain")
    result = subprocess.run(safe_cmd, capture_output=True)
    return result.stdout

@app.route("/ping_14_7")
def check_status_14_7():
    host = request.args.get("host")
    safe_host = ALLOWED_PING_HOSTS.get(host)
    if safe_host is None:
        return Response("Host not allowed", status=403, content_type="text/plain")
    result = subprocess.run(["ping", "-c", "1", safe_host], capture_output=True)
    return result.stdout

@app.route("/search_14_8")
def search_14_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return Response(str(cursor.fetchall()), content_type="text/plain")

@app.route("/calc_14_9")
def calculate_14_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return Response(str(result), content_type="text/plain")
