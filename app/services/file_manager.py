import os
from flask import request, Flask, send_file, jsonify

app = Flask(__name__)

UPLOAD_BASE_DIR = "/data/uploads"

def _safe_path(user_path):
    safe = os.path.realpath(os.path.join(UPLOAD_BASE_DIR, os.path.basename(user_path)))
    if not safe.startswith(UPLOAD_BASE_DIR):
        return None
    return safe

@app.route("/api/files/read")
def read_file():
    filepath = request.args.get("path", "")
    full_path = _safe_path(filepath)
    if full_path is None:
        return {"error": "Forbidden"}, 403
    with open(full_path, "r") as f:
        content = f.read()
    return jsonify({"content": content})

@app.route("/api/files/download")
def download_file():
    filename = request.args.get("name", "")
    full_path = _safe_path(filename)
    if full_path is None:
        return {"error": "Forbidden"}, 403
    return send_file(full_path)

@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    filepath = request.form.get("path", "")
    target = _safe_path(filepath)
    if target is None:
        return {"error": "Forbidden"}, 403
    os.remove(target)
    return {"status": "deleted"}
