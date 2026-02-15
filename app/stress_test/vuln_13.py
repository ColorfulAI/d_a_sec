import subprocess
import shlex
from flask import Flask, request, jsonify, abort
app = Flask(__name__)

ALLOWED_COMMANDS = {"echo", "date", "whoami", "uname", "hostname"}

@app.route("/stress13")
def handler_13():
    cmd = request.args.get("c", "echo hello")
    parts = shlex.split(cmd)
    if not parts or parts[0] not in ALLOWED_COMMANDS:
        abort(400, description="Command not allowed")
    out = subprocess.check_output(parts, shell=False)
    return jsonify({"output": out.decode()})
