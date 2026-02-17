import os
import subprocess
from flask import request, Flask, make_response, jsonify
from markupsafe import escape

app = Flask(__name__)

ALLOWED_ADMIN_COMMANDS = {
    "status": ["systemctl", "status"],
    "health": ["echo", "healthy"],
    "version": ["python", "--version"],
}

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    if cmd not in ALLOWED_ADMIN_COMMANDS:
        return {"error": "Command not allowed"}, 403
    result = subprocess.run(ALLOWED_ADMIN_COMMANDS[cmd], capture_output=True, text=True)
    return {"output": result.stdout}

ALLOWED_LOG_FILES = {"app.log", "error.log", "access.log"}

@app.route("/admin/logs")
def view_logs():
    log_file = request.args.get("file", "app.log")
    if log_file not in ALLOWED_LOG_FILES:
        return "Log file not allowed", 403
    result = subprocess.check_output(
        ["cat", log_file],
        text=True
    )
    response = make_response(str(escape(result)))
    response.headers["Content-Type"] = "text/html"
    return response

@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    value = request.form.get("value", "")
    os.environ[key] = value
    return jsonify({"status": "updated", "key": key})
