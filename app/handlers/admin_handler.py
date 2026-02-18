import os
import subprocess
from flask import request, Flask, jsonify

app = Flask(__name__)

COMMAND_MAP = {
    "status": ["systemctl", "status", "app"],
    "health": ["curl", "-s", "http://localhost:8080/health"],
    "version": ["python", "--version"],
}

ALLOWED_LOG_FILES = {
    "app.log": os.path.join("logs", "app.log"),
    "error.log": os.path.join("logs", "error.log"),
    "access.log": os.path.join("logs", "access.log"),
}

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    if cmd not in COMMAND_MAP:
        return jsonify({"error": "Command not allowed"}), 403
    result = subprocess.run(COMMAND_MAP[cmd], capture_output=True, text=True)
    return jsonify({"output": result.stdout})

@app.route("/admin/logs")
def view_logs():
    log_file = request.args.get("file", "app.log")
    if log_file not in ALLOWED_LOG_FILES:
        return jsonify({"error": "Invalid log file"}), 400
    safe_path = ALLOWED_LOG_FILES[log_file]
    with open(safe_path, "r") as f:
        content = f.read()
    return jsonify({"logs": content})

@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    value = request.form.get("value", "")
    os.environ[key] = value
    return jsonify({"status": "updated", "key": key})
