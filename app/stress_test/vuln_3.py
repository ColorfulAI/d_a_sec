import subprocess
from flask import Flask, request, jsonify, abort
app = Flask(__name__)

ALLOWED_COMMANDS = {
    "echo hello": ["echo", "hello"],
}

@app.route("/stress3")
def handler_3():
    cmd_key = request.args.get("c", "echo hello")
    cmd = ALLOWED_COMMANDS.get(cmd_key)
    if cmd is None:
        abort(400, description="Command not allowed")
    out = subprocess.check_output(cmd)
    return jsonify({"output": out.decode()})
