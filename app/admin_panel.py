"""Admin panel endpoint for server diagnostics."""
import re
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

_VALID_HOST_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


@app.route("/admin/ping")
def ping_server():
    host = request.args.get("host")
    if not host or not _VALID_HOST_RE.match(host):
        return jsonify({"error": "Invalid host"}), 400
    result = subprocess.run(
        ["ping", "-c", "1", host], capture_output=True, text=True
    )
    return jsonify({"output": result.stdout})
