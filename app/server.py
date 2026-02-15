import ast
import operator
import os
from flask import Flask, request, redirect, render_template_string, jsonify

app = Flask(__name__)

def get_db():
    import sqlite3
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
    "home": "/",
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
    if isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPS:
        return SAFE_OPS[type(node.op)](safe_eval(node.left), safe_eval(node.right))
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
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

ALLOWED_FILES = {"README.md": "/data/README.md", "info.txt": "/data/info.txt", "help.txt": "/data/help.txt"}

@app.route("/read")
def read_file():
    filename = request.args.get("file", "README.md")
    path = ALLOWED_FILES.get(filename)
    if path is None:
        return "File not allowed", 403
    with open(path) as f:
        return f.read()

@app.route("/render")
def render_page():
    template = request.args.get("template", "<h1>Hello</h1>")
    return render_template_string(template)

if __name__ == "__main__":
    app.run(host="0.0.0.0")
