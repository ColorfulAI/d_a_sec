import os
import subprocess
from flask import request, Flask, jsonify, make_response
from markupsafe import escape

app = Flask(__name__)

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    allowed_commands = {"status": "status", "info": "info", "version": "version"}
    if cmd not in allowed_commands:
        return jsonify({"error": "Command not allowed"}), 403
    safe_cmd = allowed_commands[cmd]
    output = subprocess.run([safe_cmd], capture_output=True, text=True).stdout
    return jsonify({"output": output})

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
