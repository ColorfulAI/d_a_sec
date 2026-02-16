import os
import subprocess
from flask import request, Flask, make_response

app = Flask(__name__)

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    ALLOWED_COMMANDS = {"status": "status", "health": "health", "version": "version"}
    if cmd not in ALLOWED_COMMANDS:
        return {"error": "Command not allowed"}, 403
    safe_cmd = ALLOWED_COMMANDS[cmd]
    output = subprocess.check_output([safe_cmd], text=True)
    return {"output": output}

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
