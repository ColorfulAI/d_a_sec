import re
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

VALID_HOST_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


@app.route("/tools/ping")
def ping_host():
    host = request.args.get("host", "localhost")
    if not VALID_HOST_PATTERN.match(host):
        return jsonify({"error": "invalid host"}), 400
    result = subprocess.check_output(["ping", "-c", "1", host])
    return jsonify({"output": result.decode()})
