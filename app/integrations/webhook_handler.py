import requests
from urllib.parse import urlparse, urlunparse
from flask import Flask, request as flask_request, jsonify

app = Flask(__name__)

ALLOWED_WEBHOOK_HOSTS = {"hooks.slack.com", "discord.com", "api.github.com"}


@app.route("/integrations/webhook/test", methods=["POST"])
def test_webhook():
    callback_url = flask_request.json.get("callback_url", "")
    payload = flask_request.json.get("payload", {})
    if not callback_url:
        return jsonify({"error": "callback_url required"}), 400
    parsed = urlparse(callback_url)
    if parsed.scheme not in ("https",):
        return jsonify({"error": "only https allowed"}), 400
    if parsed.hostname not in ALLOWED_WEBHOOK_HOSTS:
        return jsonify({"error": "callback_url host not allowed"}), 400
    safe_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    resp = requests.post(safe_url, json=payload, timeout=10)
    return jsonify({"status": resp.status_code, "body": resp.text[:500]})
