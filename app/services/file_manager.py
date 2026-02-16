import os
from flask import request, Flask, send_file, abort, jsonify
from werkzeug.utils import safe_join

app = Flask(__name__)

UPLOAD_DIR = "/data/uploads"

@app.route("/api/files/read")
def read_file():
    filepath = request.args.get("path", "")
    full_path = safe_join(UPLOAD_DIR, filepath)
    if full_path is None:
        abort(403)
    with open(full_path, "r") as f:
        content = f.read()
    return {"content": content}

@app.route("/api/files/download")
def download_file():
    filename = request.args.get("name", "")
    safe = safe_join(UPLOAD_DIR, filename)
    if safe is None:
        abort(403)
    return send_file(safe)

@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    filepath = request.form.get("path", "")
    target = safe_join(UPLOAD_DIR, filepath)
    if target is None:
        abort(403)
    os.remove(target)
    return {"status": "deleted"}
