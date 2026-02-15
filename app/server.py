import sqlite3
import subprocess
from flask import Flask, request, redirect

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
    return {"results": results}

@app.route("/run")
def run_command():
    cmd = request.args.get("cmd", "echo hello")
    output = subprocess.check_output(cmd, shell=True)
    return {"output": output.decode()}

@app.route("/redirect")
def open_redirect():
    url = request.args.get("url", "/")
    return redirect(url)

if __name__ == "__main__":
    app.run(debug=True)
