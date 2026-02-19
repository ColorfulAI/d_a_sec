from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/test")
def test_page():
    return jsonify({"status": "ok", "page": "test"})
