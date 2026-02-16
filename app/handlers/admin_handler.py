import os
import subprocess
from flask import request, Flask, make_response, jsonify

app = Flask(__name__)

ALLOWED_COMMANDS = {
    "status": ["status"],
    "health": ["health"],
    "version": ["version"],
    "uptime": ["uptime"],
}

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    cmd_args = ALLOWED_COMMANDS.get(cmd)
    if cmd_args is None:
        return {"error": "command not allowed"}, 403
    output = subprocess.run(
        cmd_args, capture_output=True, text=True
    ).stdout
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
    return jsonify({"status": "updated", "key": key})
