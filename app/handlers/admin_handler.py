import os
import subprocess
from flask import request, Flask

app = Flask(__name__)

ALLOWED_COMMANDS = {
    "status": ["systemctl", "status", "app"],
    "logs": ["journalctl", "-u", "app", "--no-pager", "-n", "100"],
    "disk": ["df", "-h"],
    "memory": ["free", "-m"],
}

ALLOWED_LOG_FILES = {
    "app": "app.log",
    "error": "error.log",
    "access": "access.log",
}

ALLOWED_CONFIG_KEYS = {
    "APP_DEBUG",
    "APP_LOG_LEVEL",
    "APP_TIMEOUT",
}

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd_name = request.form.get("command", "")
    if cmd_name not in ALLOWED_COMMANDS:
        return {"error": "Command not allowed"}, 400
    result = subprocess.run(ALLOWED_COMMANDS[cmd_name], capture_output=True, text=True)
    return {"output": result.stdout}

@app.route("/admin/logs")
def view_logs():
    log_name = request.args.get("file", "app")
    if log_name not in ALLOWED_LOG_FILES:
        return {"error": "Log file not allowed"}, 400
    log_file = ALLOWED_LOG_FILES[log_name]
    result = subprocess.check_output(
        ["cat", log_file],
        text=True
    )
    return {"output": result}

@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    if key not in ALLOWED_CONFIG_KEYS:
        return {"error": "Config key not allowed"}, 400
    value = request.form.get("value", "")
    os.environ[key] = value
    return {"status": "updated"}
