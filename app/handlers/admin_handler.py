import os
import subprocess
from flask import request, Flask, jsonify, make_response
from markupsafe import escape

app = Flask(__name__)

ALLOWED_COMMANDS = {"status": "status", "version": "version", "uptime": "uptime", "df": "df", "free": "free"}

@app.route("/admin/execute", methods=["POST"])
def execute_command():
    cmd = request.form.get("command", "")
    safe_cmd = ALLOWED_COMMANDS.get(cmd)
    if safe_cmd is None:
        return jsonify(error="Command not allowed"), 403
    output = subprocess.run([safe_cmd], capture_output=True, text=True, check=False).stdout
    return jsonify(output=output)

@app.route("/admin/logs")
def view_logs():
    log_file = request.args.get("file", "app.log")
    safe_name = os.path.basename(log_file)
    safe_path = os.path.join("/var/log/app", safe_name)
    result = subprocess.check_output(
        ["cat", safe_path],
        text=True
    )
    response = make_response(str(escape(result)))
    response.headers["Content-Type"] = "text/html"
    return response

@app.route("/admin/config", methods=["POST"])
def update_config():
    key = request.form.get("key", "")
    value = request.form.get("value", "")
    os.environ[key] = value
    return jsonify(status="updated", key=key)
