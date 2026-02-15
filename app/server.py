import sqlite3
import os
import ast
import operator
from flask import Flask, request, redirect, jsonify, render_template_string

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect("app.db")
    return conn

@app.route("/search")
def search():
    query = request.args.get("q", "")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (query,))
    results = cursor.fetchall()
    return jsonify(results)

ALLOWED_REDIRECTS = {
    "home": "/home",
    "login": "/login",
    "dashboard": "/dashboard",
}

@app.route("/redirect")
def open_redirect():
    target = request.args.get("url", "home")
    url = ALLOWED_REDIRECTS.get(target, "/")
    return redirect(url)

SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

def safe_eval(node):
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPS:
        return SAFE_OPS[type(node.op)](safe_eval(node.left), safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -safe_eval(node.operand)
    raise ValueError("Unsupported expression")

@app.route("/eval")
def evaluate():
    expr = request.args.get("expr", "1+1")
    try:
        tree = ast.parse(expr, mode="eval")
        result = safe_eval(tree)
    except (ValueError, SyntaxError):
        return "Invalid expression", 400
    return str(result)

ALLOWED_FILES = {
    "README.md": "/data/README.md",
    "info.txt": "/data/info.txt",
    "help.txt": "/data/help.txt",
}

@app.route("/read")
def read_file():
    filename = request.args.get("file", "README.md")
    path = ALLOWED_FILES.get(filename)
    if path is None:
        return "File not allowed", 403
    with open(path) as f:
        content = f.read()
    return jsonify(content=content)

ALLOWED_TEMPLATES = {
    "hello": "<h1>Hello</h1>",
    "welcome": "<h1>Welcome, {{ name }}!</h1>",
    "goodbye": "<h1>Goodbye!</h1>",
}

@app.route("/render")
def render_page():
    template_key = request.args.get("template", "hello")
    name = request.args.get("name", "Guest")
    template = ALLOWED_TEMPLATES.get(template_key, ALLOWED_TEMPLATES["hello"])
    return render_template_string(template, name=name)

if __name__ == "__main__":
    app.run(host="0.0.0.0")
