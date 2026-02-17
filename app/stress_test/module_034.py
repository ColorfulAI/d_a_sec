"""Stress test module 34 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_READ_PATHS = {
    "log": "/var/data/log.txt",
    "config": "/var/data/config.txt",
}
ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com",
}
ALLOWED_CMDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
}
ALLOWED_HOSTS = {
    "localhost": "127.0.0.1",
    "google": "8.8.8.8",
}
ALLOWED_CAT_FILES = {
    "readme": "readme.txt",
    "config": "config.txt",
    "status": "status.txt",
}

@app.route("/query_34_0")
def query_db_34_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_34_1")
def run_cmd_34_1():
    filename = request.args.get("file")
    if filename not in ALLOWED_CAT_FILES:
        return "File not allowed", 403
    subprocess.run(["cat", ALLOWED_CAT_FILES[filename]], check=False)
    return "done"

@app.route("/read_34_2")
def read_file_34_2():
    path = request.args.get("path")
    if path not in ALLOWED_READ_PATHS:
        return "Access denied", 403
    with open(ALLOWED_READ_PATHS[path], "r") as f:
        return escape(f.read())

@app.route("/render_34_3")
def render_page_34_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_34_4")
def fetch_url_34_4():
    url = request.args.get("url")
    if url not in ALLOWED_URLS:
        return "Forbidden", 403
    resp = urllib.request.urlopen(ALLOWED_URLS[url])
    return resp.read()

@app.route("/load_34_5")
def load_data_34_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_34_6")
def process_34_6():
    cmd = request.args.get("cmd")
    if cmd not in ALLOWED_CMDS:
        return "Command not allowed", 403
    result = subprocess.run(ALLOWED_CMDS[cmd], capture_output=True)
    return result.stdout

@app.route("/ping_34_7")
def check_status_34_7():
    host = request.args.get("host")
    if host not in ALLOWED_HOSTS:
        return "Host not allowed", 403
    result = subprocess.run(["ping", "-c", "1", ALLOWED_HOSTS[host]], capture_output=True)
    return result.stdout

@app.route("/search_34_8")
def search_34_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return str(cursor.fetchall())

@app.route("/calc_34_9")
def calculate_34_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
