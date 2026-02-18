import os
from flask import request, Flask, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_DIR = "/data/uploads"


@app.route("/api/files/read")
def read_file():
    filepath = request.args.get("path", "")
    safe_name = secure_filename(filepath)
    full_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(full_path, "r") as f:
        content = f.read()
    return jsonify(content=content)


@app.route("/api/files/download")
def download_file():
    filename = request.args.get("name", "")
    safe_name = secure_filename(filename)
    return send_file(os.path.join(UPLOAD_DIR, safe_name))


@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    filepath = request.form.get("path", "")
    safe_name = secure_filename(filepath)
    target = os.path.join(UPLOAD_DIR, safe_name)
    os.remove(target)
    return {"status": "deleted"}
