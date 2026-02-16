import os
import subprocess
from flask import request, Flask, make_response

app = Flask(__name__)

ALLOWED_COMMANDS = {
    "status": ["systemctl", "status", "app"],
    "uptime": ["uptime"],
    "disk": ["df", "-h"],
}

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd_name = request.form.get("command", "")
    if cmd_name not in ALLOWED_COMMANDS:
        return {"error": "Command not allowed"}, 403
    result = subprocess.run(ALLOWED_COMMANDS[cmd_name], capture_output=True, text=True)
    return {"output": result.stdout}

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
    return {"status": "updated", "key": key}
