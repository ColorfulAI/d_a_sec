import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)


def get_export_db():
    conn = sqlite3.connect("exports.db")
    return conn


@app.route("/export/query")
def export_data():
    table_name = request.args.get("table", "users")
    filter_col = request.args.get("column", "id")
    filter_val = request.args.get("value", "1")
    db = get_export_db()
    cursor = db.cursor()
    query = "SELECT * FROM " + table_name + " WHERE " + filter_col + " = '" + filter_val + "'"
    cursor.execute(query)
    results = cursor.fetchall()
    return jsonify(results)
