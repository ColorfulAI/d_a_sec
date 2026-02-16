import os
from flask import request, Flask, make_response, jsonify
from markupsafe import escape

app = Flask(__name__)

ALLOWED_COMMANDS = {"status", "health", "version"}
ALLOWED_LOG_PATHS = {
    "app.log": os.path.join("logs", "app.log"),
    "error.log": os.path.join("logs", "error.log"),
    "access.log": os.path.join("logs", "access.log"),
    "debug.log": os.path.join("logs", "debug.log"),
}

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    if cmd not in ALLOWED_COMMANDS:
        return jsonify({"error": "Command not allowed"}), 400
    return jsonify({"output": cmd})

@app.route("/admin/logs")
def view_logs():
    log_file = request.args.get("file", "app.log")
    safe_path = ALLOWED_LOG_PATHS.get(log_file)
    if safe_path is None:
        return jsonify({"error": "Invalid log file name"}), 400
    with open(safe_path, "r") as f:
        content = f.read()
    response = make_response(str(escape(content)))
    response.headers["Content-Type"] = "text/html"
    return response

@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    value = request.form.get("value", "")
    os.environ[key] = value
    return jsonify({"status": "updated", "key": key})
