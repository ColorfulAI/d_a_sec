import sqlite3
import subprocess
from flask import request, Flask, jsonify

app = Flask(__name__)

@app.route("/api/users")
def get_user():
    username = request.args.get("username", "")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    results = cursor.fetchall()
    conn.close()
    return jsonify({"users": results})

@app.route("/api/users/search")
def search_users():
    term = request.args.get("q", "")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name LIKE ?", ("%" + term + "%",))
    results = cursor.fetchall()
    conn.close()
    return jsonify({"results": results})

@app.route("/api/run-report")
def run_report():
    report_name = request.args.get("report", "")
    result = subprocess.run(
        ["python", "generate_report.py", report_name],
        capture_output=True, text=True
    )
    return jsonify({"output": result.stdout})
