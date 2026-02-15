import sqlite3
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

ALLOWED_TABLES = {"users": "users", "orders": "orders", "products": "products", "exports": "exports"}
ALLOWED_COLUMNS = {"id": "id", "name": "name", "email": "email", "status": "status", "created_at": "created_at", "updated_at": "updated_at"}


def get_export_db():
    conn = sqlite3.connect("exports.db")
    return conn


@app.route("/export/query")
def export_data():
    table_name = ALLOWED_TABLES.get(request.args.get("table", "users"))
    filter_col = ALLOWED_COLUMNS.get(request.args.get("column", "id"))
    filter_val = request.args.get("value", "1")
    if table_name is None:
        abort(400, "Invalid table name")
    if filter_col is None:
        abort(400, "Invalid column name")
    db = get_export_db()
    cursor = db.cursor()
    query = "SELECT * FROM " + table_name + " WHERE " + filter_col + " = ?"
    cursor.execute(query, (filter_val,))
    results = cursor.fetchall()
    return jsonify(results)
