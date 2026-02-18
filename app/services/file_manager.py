import os
from flask import request, Flask, send_file, jsonify, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

BASE_DIR = "/data/uploads"


@app.route("/api/files/read")
def read_file():
    filepath = request.args.get("path", "")
    safe_name = secure_filename(filepath)
    if not safe_name:
        abort(400)
    full_path = os.path.join(BASE_DIR, safe_name)
    with open(full_path, "r") as f:
        content = f.read()
    return jsonify({"content": content})


@app.route("/api/files/download")
def download_file():
    filename = request.args.get("name", "")
    safe_name = secure_filename(filename)
    if not safe_name:
        abort(400)
    full_path = os.path.join(BASE_DIR, safe_name)
    return send_file(full_path)


@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    filepath = request.form.get("path", "")
    safe_name = secure_filename(filepath)
    if not safe_name:
        abort(400)
    target = os.path.join(BASE_DIR, safe_name)
    os.remove(target)
    return jsonify({"status": "deleted"})
