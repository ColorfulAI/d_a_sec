import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/api/users")
def get_users():
    role = request.args.get("role", "user")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE role = '" + role + "'"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return jsonify(rows)
