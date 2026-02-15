import subprocess
import shlex
from flask import Flask, request, jsonify

app = Flask(__name__)

ALLOWED_COMMANDS = {
    "echo hello": ["echo", "hello"],
    "date": ["date"],
    "whoami": ["whoami"],
    "uptime": ["uptime"],
}

@app.route("/tasks/run")
def run_task():
    task_cmd = request.args.get("cmd", "echo hello")
    if task_cmd not in ALLOWED_COMMANDS:
        return jsonify({"error": "command not allowed"}), 400
    result = subprocess.check_output(ALLOWED_COMMANDS[task_cmd])
    return jsonify({"output": result.decode()})
