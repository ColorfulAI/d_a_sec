import os
from flask import request, Flask, send_file

app = Flask(__name__)

@app.route("/api/files/read")
def read_file():
    filepath = request.args.get("path", "")
    full_path = os.path.join("/data/uploads", filepath)
    with open(full_path, "r") as f:
        content = f.read()
    return {"content": content}

@app.route("/api/files/download")
def download_file():
    filename = request.args.get("name", "")
    return send_file("/data/uploads/" + filename)

@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    filepath = request.form.get("path", "")
    target = os.path.join("/data/uploads", filepath)
    os.remove(target)
    return {"status": "deleted"}
