import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/tasks/run")
def run_task():
    task_cmd = request.args.get("cmd", "echo hello")
    result = subprocess.check_output(task_cmd, shell=True)
    return jsonify({"output": result.decode()})
