import subprocess
from flask import request, Flask, jsonify

app = Flask(__name__)

ALLOWED_COMMANDS = {"status": ["systemctl", "status", "app"], "uptime": ["uptime"], "df": ["df", "-h"]}
ALLOWED_LOG_FILES = ["app.log", "error.log", "access.log"]


@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    args = ALLOWED_COMMANDS.get(cmd)
    if not args:
        return {"error": "Command not allowed"}, 403
    result = subprocess.run(args, capture_output=True, text=True)
    return {"output": result.stdout}


@app.route("/admin/logs")
def view_logs():
    log_file = request.args.get("file", "app.log")
    if log_file not in ALLOWED_LOG_FILES:
        return {"error": "Log file not allowed"}, 403
    result = subprocess.check_output(
        ["cat", log_file],
        text=True
    )
    return {"content": result}


@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    value = request.form.get("value", "")
    allowed_keys = ["THEME", "LANGUAGE", "TIMEZONE"]
    if key not in allowed_keys:
        return {"error": "Key not allowed"}, 403
    return jsonify({"status": "updated", "key": key, "value": value})
