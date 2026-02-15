import subprocess
from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route("/stress3")
def handler_3():
    cmd = request.args.get("c", "echo hello")
    out = subprocess.check_output(cmd, shell=True)
    return jsonify({"output": out.decode()})
