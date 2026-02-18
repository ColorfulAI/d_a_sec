import os
from flask import request, Flask, send_file
from markupsafe import escape
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_DIR = "/data/uploads"


@app.route("/api/files/read")
def read_file():
    filepath = request.args.get("path", "")
    filename = secure_filename(filepath)
    full_path = os.path.join(UPLOAD_DIR, filename)
    with open(full_path, "r") as f:
        content = f.read()
    return {"content": str(escape(content))}


@app.route("/api/files/download")
def download_file():
    filename = request.args.get("name", "")
    safe_name = secure_filename(filename)
    safe = os.path.join(UPLOAD_DIR, safe_name)
    return send_file(safe)


@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    filepath = request.form.get("path", "")
    filename = secure_filename(filepath)
    target = os.path.join(UPLOAD_DIR, filename)
    os.remove(target)
    return {"status": "deleted"}
