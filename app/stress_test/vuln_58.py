import shlex
import subprocess
from flask import Flask, request, jsonify, abort
app = Flask(__name__)

ALLOWED_COMMANDS = {"echo hello", "uptime", "date", "whoami"}

@app.route("/stress58")
def handler_58():
    cmd = request.args.get("c", "echo hello")
    if cmd not in ALLOWED_COMMANDS:
        abort(400, description="Command not allowed")
    out = subprocess.check_output(shlex.split(cmd))
    return jsonify({"output": out.decode()})
