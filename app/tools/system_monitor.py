import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/tools/ping")
def ping_host():
    host = request.args.get("host", "localhost")
    result = subprocess.check_output("ping -c 1 " + host, shell=True)
    return jsonify({"output": result.decode()})
