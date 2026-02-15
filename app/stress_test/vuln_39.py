import os
from flask import Flask, request, abort
app = Flask(__name__)
@app.route("/stress39")
def handler_39():
    filename = request.args.get("f", "readme.txt")
    safe_path = os.path.realpath(os.path.join("/data", filename))
    if not safe_path.startswith("/data/"):
        abort(403)
    with open(safe_path) as fh:
        return fh.read()
