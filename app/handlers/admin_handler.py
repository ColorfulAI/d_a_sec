import os
import subprocess
from flask import request, Flask, jsonify
from markupsafe import escape

app = Flask(__name__)

ALLOWED_COMMANDS = {
    "status": ["status"],
    "health": ["health"],
    "version": ["version"],
}

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return jsonify({"error": "Command not allowed"}), 403
    result = subprocess.run(
        safe_cmd,
        capture_output=True, text=True
    )
    return jsonify({"output": result.stdout})

ALLOWED_LOG_FILES = {
    "app.log": os.path.join("logs", "app.log"),
    "error.log": os.path.join("logs", "error.log"),
    "access.log": os.path.join("logs", "access.log"),
}

@app.route("/admin/logs")
def view_logs():
    log_file = request.args.get("file", "app.log")
    safe_path = ALLOWED_LOG_FILES.get(log_file)
    if safe_path is None:
        return jsonify({"error": "Invalid log file"}), 400
    with open(safe_path, "r") as f:
        content = f.read()
    return jsonify({"content": content})

@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    value = request.form.get("value", "")
    os.environ[key] = value
    return jsonify({"status": "updated", "key": str(escape(key))})
