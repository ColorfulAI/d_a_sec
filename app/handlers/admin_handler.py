import os
from flask import request, Flask, jsonify

app = Flask(__name__)

ALLOWED_COMMANDS = {"status", "health", "version", "uptime"}

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    if cmd not in ALLOWED_COMMANDS:
        return jsonify({"error": "Command not allowed"}), 403
    return jsonify({"output": cmd})

ALLOWED_LOG_FILES = {"app.log": "app.log", "error.log": "error.log", "access.log": "access.log"}

@app.route("/admin/logs")
def view_logs():
    log_file = request.args.get("file", "app.log")
    safe_path = ALLOWED_LOG_FILES.get(log_file)
    if safe_path is None:
        return jsonify({"error": "Log file not allowed"}), 403
    try:
        with open(safe_path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        return jsonify({"error": "Log file not found"}), 404
    return jsonify({"content": content})

@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    value = request.form.get("value", "")
    os.environ[key] = value
    return jsonify({"status": "updated", "key": key})
