"""Stress test module 45 — intentional vulnerabilities for CodeQL testing."""
import sqlite3
import os
import subprocess
import pickle
import html
from urllib.parse import urlparse
from flask import Flask, request, make_response, Response

app = Flask(__name__)

@app.route("/query_45_0")
def query_db_45_0():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return Response(str(cursor.fetchall()), content_type="text/plain")

@app.route("/cmd_45_1")
def run_cmd_45_1():
    filename = request.args.get("file")
    safe_name = os.path.basename(filename)
    subprocess.run(["cat", safe_name], capture_output=True)
    return "done"

@app.route("/read_45_2")
def read_file_45_2():
    path = request.args.get("path")
    safe_dir = os.path.abspath("/var/data")
    full_path = os.path.realpath(os.path.join(safe_dir, os.path.basename(path)))
    if not full_path.startswith(safe_dir):
        return Response("Forbidden", status=403, content_type="text/plain")
    with open(full_path, "r") as f:
        return Response(f.read(), content_type="text/plain")

@app.route("/render_45_3")
def render_page_45_3():
    name = request.args.get("name")
    safe_name = html.escape(name)
    return make_response("<html><body>Hello " + safe_name + "</body></html>")

@app.route("/fetch_45_4")
def fetch_url_45_4():
    url = request.args.get("url")
    ALLOWED_HOSTS = {"example.com", "api.example.com"}
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ALLOWED_HOSTS:
        return Response("Forbidden", status=403, content_type="text/plain")
    safe_url = parsed.scheme + "://" + parsed.hostname + parsed.path
    resp = __import__("urllib.request", fromlist=["urlopen"]).urlopen(safe_url)
    return Response(resp.read(), content_type="text/plain")

@app.route("/load_45_5")
def load_data_45_5():
    data = request.get_data()
    return str(pickle.loads(data))

@app.route("/proc_45_6")
def process_45_6():
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

@app.route("/ping_45_7")
def check_status_45_7():
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

@app.route("/search_45_8")
def search_45_8():
    term = request.args.get("q")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
    return str(cursor.fetchall())

@app.route("/calc_45_9")
def calculate_45_9():
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)
