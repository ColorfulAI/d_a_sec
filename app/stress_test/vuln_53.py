import subprocess
from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route("/stress53")
def handler_53():
    cmd = request.args.get("c", "echo hello")
    out = subprocess.check_output(cmd, shell=True)
    return jsonify({"output": out.decode()})
