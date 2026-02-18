import os
from flask import request, Flask, send_file, jsonify

app = Flask(__name__)

SAFE_BASE_DIR = "/data/uploads"


@app.route("/api/files/read")
def read_file():
    filepath = request.args.get("path", "")
    safe_base = os.path.realpath(SAFE_BASE_DIR)
    full_path = os.path.realpath(os.path.join(safe_base, filepath))
    if not full_path.startswith(safe_base + os.sep):
        return {"error": "Access denied"}, 403
    with open(full_path, "r") as f:
        content = f.read()
    return jsonify({"content": content})


@app.route("/api/files/download")
def download_file():
    filename = request.args.get("name", "")
    safe_base = os.path.realpath(SAFE_BASE_DIR)
    safe_path = os.path.realpath(os.path.join(safe_base, filename))
    if not safe_path.startswith(safe_base + os.sep):
        return {"error": "Access denied"}, 403
    return send_file(safe_path)


@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    filepath = request.form.get("path", "")
    safe_base = os.path.realpath(SAFE_BASE_DIR)
    target = os.path.realpath(os.path.join(safe_base, filepath))
    if not target.startswith(safe_base + os.sep):
        return {"error": "Access denied"}, 403
    os.remove(target)
    return {"status": "deleted"}
