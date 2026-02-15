import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)


def get_analytics_db():
    conn = sqlite3.connect("analytics.db")
    return conn


@app.route("/analytics/events")
def get_events():
    event_type = request.args.get("type", "pageview")
    start_date = request.args.get("start", "2024-01-01")
    db = get_analytics_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM events WHERE type = ? AND date >= ?", (event_type, start_date))
    results = cursor.fetchall()
    return jsonify(results)
