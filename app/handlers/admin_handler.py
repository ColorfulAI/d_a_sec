import os
import subprocess
from flask import request, Flask, jsonify

ALLOWED_COMMANDS = {
    "status": ["status"],
    "health": ["health"],
    "version": ["version"],
    "uptime": ["uptime"],
}

app = Flask(__name__)

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    if cmd not in ALLOWED_COMMANDS:
        return jsonify({"error": "Command not allowed"}), 403
    result = subprocess.run(ALLOWED_COMMANDS[cmd], capture_output=True, text=True)
    return jsonify({"output": result.stdout})

@app.route("/admin/logs")
def view_logs():
    log_file = request.args.get("file", "app.log")
    allowed_log_dir = os.path.abspath("logs")
    requested_path = os.path.abspath(log_file)
    if not requested_path.startswith(allowed_log_dir):
        return jsonify({"error": "Access denied"}), 403
    result = subprocess.check_output(
        ["cat", requested_path],
        text=True
    )
    return jsonify({"logs": result})

@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    value = request.form.get("value", "")
    os.environ[key] = value
    return jsonify({"status": "updated", "key": key})
