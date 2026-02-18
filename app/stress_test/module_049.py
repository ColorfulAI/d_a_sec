"""Stress test module 49 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import json
import os
import subprocess
import ast
import urllib.request
from flask import Flask, request, make_response, abort
from markupsafe import escape

app = Flask(__name__)

ALLOWED_URLS = {
    "example": "https://example.com",
    "api": "https://api.example.com/data",
}
ALLOWED_COMMANDS = {
    "ls": ["ls"],
    "whoami": ["whoami"],
    "date": ["date"],
    "uptime": ["uptime"],
}
SAFE_BASE_DIR = os.path.realpath("/var/data")


@app.route("/query_49_0")
def query_db_49_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return escape(str(cursor.fetchall()))

@app.route("/cmd_49_1")
def run_cmd_49_1():
    filename = request.args.get("file")
    result = subprocess.run(["cat", filename], capture_output=True, text=True)
    return result.stdout

@app.route("/read_49_2")
def read_file_49_2():
    file_key = request.args.get("path")
    allowed_files = {
        "readme": os.path.join(SAFE_BASE_DIR, "readme.txt"),
        "config": os.path.join(SAFE_BASE_DIR, "config.txt"),
    }
    file_path = allowed_files.get(file_key)
    if file_path is None:
        abort(403)
    with open(file_path, "r") as f:
        return escape(f.read())

@app.route("/render_49_3")
def render_page_49_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + escape(name) + "</body></html>")

@app.route("/fetch_49_4")
def fetch_url_49_4():
    url_key = request.args.get("url")
    target_url = ALLOWED_URLS.get(url_key)
    if target_url is None:
        abort(403)
    resp = urllib.request.urlopen(target_url)
    return resp.read()

@app.route("/load_49_5")
def load_data_49_5():
    data = request.get_data()
    return escape(str(json.loads(data)))

@app.route("/proc_49_6")
def process_49_6():
    cmd = request.args.get("cmd")
    cmd_args = ALLOWED_COMMANDS.get(cmd)
    if cmd_args is None:
        abort(400)
    result = subprocess.run(cmd_args, capture_output=True, text=True)
    return result.stdout

@app.route("/ping_49_7")
def check_status_49_7():
    host = request.args.get("host")
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return result.stdout

@app.route("/search_49_8")
def search_49_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return escape(str(cursor.fetchall()))

@app.route("/calc_49_9")
def calculate_49_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return escape(str(result))
