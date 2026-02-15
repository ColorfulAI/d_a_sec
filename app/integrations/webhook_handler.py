import requests
from flask import Flask, request as flask_request, jsonify

app = Flask(__name__)


@app.route("/integrations/webhook/test", methods=["POST"])
def test_webhook():
    callback_url = flask_request.json.get("callback_url", "")
    payload = flask_request.json.get("payload", {})
    if not callback_url:
        return jsonify({"error": "callback_url required"}), 400
    resp = requests.post(callback_url, json=payload, timeout=10)
    return jsonify({"status": resp.status_code, "body": resp.text[:500]})
