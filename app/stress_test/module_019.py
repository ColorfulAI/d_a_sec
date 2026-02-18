"""Stress test module 19 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import re
import urllib.request
from flask import Flask, request, make_response
from markupsafe import escape

app = Flask(__name__)

SAFE_BASE_DIR = os.path.realpath("/var/data/files")
ALLOWED_URL_MAP = {
    "api": "https://api.example.com/data",
    "status": "https://status.example.com/check",
}
COMMAND_MAP = {"ls": "ls", "whoami": "whoami", "date": "date"}
HOST_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')

@app.route("/query_19_0")
def query_db_19_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/cmd_19_1")
def run_cmd_19_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], capture_output=True)
    return "done"

@app.route("/read_19_2")
def read_file_19_2():
    path = request.args.get("path")
    safe_name = os.path.basename(path)
    real_path = os.path.realpath(os.path.join(SAFE_BASE_DIR, safe_name))
    if not real_path.startswith(SAFE_BASE_DIR):
        return make_response("Forbidden", 403)
    with open(real_path, "r") as f:
        return make_response(escape(f.read()))

@app.route("/render_19_3")
def render_page_19_3():
    name = request.args.get("name")
    return make_response("<html><body>Hello " + str(escape(name)) + "</body></html>")

@app.route("/fetch_19_4")
def fetch_url_19_4():
    key = request.args.get("url")
    url = ALLOWED_URL_MAP.get(key)
    if url is None:
        return make_response("URL not allowed", 403)
    resp = urllib.request.urlopen(url)
    return resp.read()

@app.route("/load_19_5")
def load_data_19_5():
    data = request.get_data()
    result = json.loads(data)
    return make_response(escape(str(result)))

@app.route("/proc_19_6")
def process_19_6():
    cmd = request.args.get("cmd")
    safe_cmd = COMMAND_MAP.get(cmd)
    if safe_cmd is None:
        return make_response("Command not allowed", 403)
    result = subprocess.run([safe_cmd], capture_output=True)
    return result.stdout

@app.route("/ping_19_7")
def check_status_19_7():
    host = request.args.get("host")
    if not HOST_PATTERN.match(host):
        return make_response("Invalid host", 400)
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.stdout

@app.route("/search_19_8")
def search_19_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return make_response(escape(str(cursor.fetchall())))

@app.route("/calc_19_9")
def calculate_19_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return str(result)
