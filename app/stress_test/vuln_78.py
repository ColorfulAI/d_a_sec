import subprocess
from flask import Flask, request, jsonify
app = Flask(__name__)

ALLOWED_COMMANDS = {
    "echo hello": ["echo", "hello"],
    "date": ["date"],
    "whoami": ["whoami"],
    "uptime": ["uptime"],
}

@app.route("/stress78")
def handler_78():
    cmd = request.args.get("c", "echo hello")
    if cmd not in ALLOWED_COMMANDS:
        return jsonify({"error": "command not allowed"}), 400
    out = subprocess.check_output(ALLOWED_COMMANDS[cmd])
    return jsonify({"output": out.decode()})
