import os
import subprocess
from flask import request, Flask, jsonify
from markupsafe import escape

app = Flask(__name__)

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    allowed_commands = {"status": "status", "health": "health", "version": "version"}
    safe_cmd = allowed_commands.get(cmd)
    if safe_cmd is None:
        return jsonify({"error": "Command not allowed"}), 403
    result = subprocess.run([safe_cmd], capture_output=True, text=True)
    return jsonify({"output": result.stdout})

@app.route("/admin/logs")
def view_logs():
    log_file = request.args.get("file", "app.log")
    allowed_logs = {"app.log": "app.log", "error.log": "error.log", "access.log": "access.log"}
    safe_path = allowed_logs.get(log_file)
    if safe_path is None:
        return jsonify({"error": "Invalid log file"}), 400
    with open(safe_path, "r") as f:
        result = f.read()
    escaped_result = str(escape(result))
    response = Flask.response_class(escaped_result, content_type="text/html")
    return response

@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    value = request.form.get("value", "")
    allowed_keys = {"DEBUG", "LOG_LEVEL", "MAINTENANCE_MODE"}
    if key not in allowed_keys:
        return jsonify({"error": "Invalid config key"}), 400
    os.environ[key] = value
    return jsonify({"status": "updated", "key": key})
