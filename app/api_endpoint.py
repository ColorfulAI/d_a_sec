"""API endpoint for user profile lookup."""
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/api/user")
def get_user_profile():
    user_id = request.args.get("id")
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = '" + user_id + "'")
    result = cursor.fetchone()
    conn.close()
    if result:
        return jsonify({"id": result[0], "name": result[1], "email": result[2]})
    return jsonify({"error": "User not found"}), 404
