import os
import subprocess
from flask import request, Flask, make_response

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
