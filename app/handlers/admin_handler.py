import os
import subprocess
from flask import request, Flask, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    allowed_commands = {
        "status": ["systemctl", "status"],
        "health": ["echo", "healthy"],
        "version": ["python", "--version"],
    }
    if cmd not in allowed_commands:
        return {"error": "Command not allowed"}, 403
    result = subprocess.run(allowed_commands[cmd], capture_output=True, text=True)
    return {"output": result.stdout}

@app.route("/admin/logs")
def view_logs():
    log_file = request.args.get("file", "app.log")
    allowed_logs = {"app.log": "app.log", "error.log": "error.log", "access.log": "access.log"}
    if log_file not in allowed_logs:
        return {"error": "Log file not allowed"}, 403
    safe_path = allowed_logs[log_file]
    with open(safe_path, "r") as f:
        result = f.read()
    response = make_response(str(escape(result)))
    response.headers["Content-Type"] = "text/html"
    return response

@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    value = request.form.get("value", "")
    allowed_keys = {"APP_MODE", "LOG_LEVEL", "DEBUG"}
    if key not in allowed_keys:
        return {"error": "Config key not allowed"}, 403
    os.environ[key] = value
    return {"status": "updated"}
