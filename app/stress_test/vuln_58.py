import subprocess
from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route("/stress58")
def handler_58():
    cmd = request.args.get("c", "echo hello")
    out = subprocess.check_output(cmd, shell=True)
    return jsonify({"output": out.decode()})
