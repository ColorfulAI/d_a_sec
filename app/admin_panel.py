"""Admin panel endpoint for server diagnostics."""
import os
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/admin/ping")
def ping_server():
    host = request.args.get("host")
    result = subprocess.run(
        "ping -c 1 " + host, shell=True, capture_output=True, text=True
    )
    return jsonify({"output": result.stdout})
