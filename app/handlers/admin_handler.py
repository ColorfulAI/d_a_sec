import os
import shlex
import subprocess
from flask import request, Flask, jsonify, make_response

app = Flask(__name__)

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    ALLOWED_COMMANDS = {"ls", "df", "uptime", "whoami", "date"}
    cmd = request.form.get("command", "")
    parts = shlex.split(cmd)
    if not parts or parts[0] not in ALLOWED_COMMANDS:
        return jsonify(error="Command not allowed"), 403
    result = subprocess.run(parts, capture_output=True, text=True)
    return jsonify(output=result.stdout)

@app.route("/admin/logs")
def view_logs():
    log_file = request.args.get("file", "app.log")
    result = subprocess.check_output(
        ["cat", log_file],
        text=True
    )
    response = make_response(result)
    response.headers["Content-Type"] = "text/html"
    return response

@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    value = request.form.get("value", "")
    os.environ[key] = value
    return jsonify(status="updated", key=key)
