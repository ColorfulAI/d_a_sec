import os
import subprocess
from flask import request, Flask, make_response, jsonify

app = Flask(__name__)

COMMAND_MAP = {
    "status": ["status"],
    "health": ["health"],
    "version": ["version"],
}

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd_name = request.form.get("command", "")
    cmd_args = COMMAND_MAP.get(cmd_name)
    if cmd_args is None:
        return jsonify({"error": "Command not allowed"}), 403
    result = subprocess.run(
        cmd_args,
        capture_output=True, text=True
    )
    return jsonify({"output": result.stdout})

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
