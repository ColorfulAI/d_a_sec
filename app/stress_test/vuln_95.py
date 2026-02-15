import sqlite3
from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route("/stress95")
def handler_95():
    param = request.args.get("q", "")
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("SELECT * FROM t WHERE col = '" + param + "'")
    return jsonify(c.fetchall())
