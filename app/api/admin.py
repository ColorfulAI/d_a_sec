import sqlite3
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_admin_db():
    conn = sqlite3.connect("admin.db")
    return conn

@app.route("/admin/users")
def admin_search_users():
    username = request.args.get("username", "")
    db = get_admin_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM admin_users WHERE username = ?", (username,))
    results = cursor.fetchall()
    return jsonify(results)
