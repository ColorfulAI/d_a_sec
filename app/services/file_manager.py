import os
from flask import request, Flask, abort, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_DIR = "/data/uploads"


@app.route("/api/files/read")
def read_file():
    filepath = request.args.get("path", "")
    safe_name = secure_filename(filepath)
    if not safe_name:
        abort(400)
    safe_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(safe_path, "r") as f:
        content = f.read()
    return jsonify(content=content)

@app.route("/api/files/download")
def download_file():
    filename = request.args.get("name", "")
    safe_name = secure_filename(filename)
    if not safe_name:
        abort(400)
    return send_from_directory(UPLOAD_DIR, safe_name)

@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    filepath = request.form.get("path", "")
    safe_name = secure_filename(filepath)
    if not safe_name:
        abort(400)
    safe_path = os.path.join(UPLOAD_DIR, safe_name)
    os.remove(safe_path)
    return jsonify(status="deleted")
