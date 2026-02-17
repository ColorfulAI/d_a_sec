"""Stress test module 1 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import json
import ast
import re
import urllib.request
from flask import Flask, request, jsonify
from markupsafe import escape

app = Flask(__name__)

ALLOWED_URLS = {
    "service1": "https://api.example.com/service1",
    "service2": "https://api.example.com/service2",
}
ALLOWED_COMMANDS = {"ls": ["ls"], "whoami": ["whoami"], "date": ["date"]}
SAFE_BASE_DIR = "/data/uploads"


@app.route("/query_1_0")
def query_db_1_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return jsonify({"results": cursor.fetchall()})


@app.route("/cmd_1_1")
def run_cmd_1_1():
    filename = request.args.get("file")
    safe_base = os.path.realpath(SAFE_BASE_DIR)
    safe_path = os.path.realpath(os.path.join(safe_base, filename))
    if not safe_path.startswith(safe_base + os.sep):
        return {"error": "Access denied"}, 403
    with open(safe_path, "r") as f:
        return jsonify({"output": f.read()})


@app.route("/read_1_2")
def read_file_1_2():
    path = request.args.get("path")
    safe_base = os.path.realpath(SAFE_BASE_DIR)
    full_path = os.path.realpath(os.path.join(safe_base, path))
    if not full_path.startswith(safe_base + os.sep):
        return {"error": "Access denied"}, 403
    with open(full_path, "r") as f:
        return jsonify({"content": f.read()})


@app.route("/render_1_3")
def render_page_1_3():
    name = request.args.get("name")
    return "<html><body>Hello " + str(escape(name)) + "</body></html>"


@app.route("/fetch_1_4")
def fetch_url_1_4():
    key = request.args.get("url")
    url = ALLOWED_URLS.get(key)
    if not url:
        return {"error": "URL not allowed"}, 403
    resp = urllib.request.urlopen(url)
    return resp.read()


@app.route("/load_1_5")
def load_data_1_5():
    data = request.get_data()
    return jsonify({"result": json.loads(data)})


@app.route("/proc_1_6")
def process_1_6():
    cmd = request.args.get("cmd")
    args = ALLOWED_COMMANDS.get(cmd)
    if not args:
        return {"error": "Command not allowed"}, 403
    result = subprocess.run(args, capture_output=True, text=True)
    return {"output": result.stdout}


@app.route("/ping_1_7")
def check_status_1_7():
    host = request.args.get("host")
    if not host or not re.match(r'^[a-zA-Z0-9._-]+$', host):
        return {"error": "Invalid hostname"}, 400
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True)
    return {"output": result.stdout}


@app.route("/search_1_8")
def search_1_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", ("%" + term + "%",))
    return jsonify({"results": cursor.fetchall()})


@app.route("/calc_1_9")
def calculate_1_9():
    expr = request.args.get("expr")
    result = ast.literal_eval(expr)
    return {"result": str(result)}
