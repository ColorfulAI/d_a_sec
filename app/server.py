import sqlite3
import subprocess
import os
import json
import hashlib
from flask import Flask, request, redirect, make_response, jsonify, render_template_string

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect("app.db")
    return conn

@app.route("/search")
def search():
    query = request.args.get("q", "")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE name = '" + query + "'")
    results = cursor.fetchall()
    return str(results)

@app.route("/run")
def run_command():
    cmd = request.args.get("cmd", "echo hello")
    output = subprocess.check_output(cmd, shell=True)
    return output.decode()

@app.route("/redirect")
def open_redirect():
    url = request.args.get("url", "/")
    return redirect(url)

@app.route("/eval")
def evaluate():
    expr = request.args.get("expr", "1+1")
    result = eval(expr)
    return str(result)

@app.route("/read")
def read_file():
    filename = request.args.get("file", "README.md")
    path = os.path.join("/data", filename)
    with open(path) as f:
        return f.read()

@app.route("/render")
def render_page():
    template = request.args.get("template", "<h1>Hello</h1>")
    return render_template_string(template)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
