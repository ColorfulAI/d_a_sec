import json

import yaml
from flask import request, Flask, jsonify
from markupsafe import escape

app = Flask(__name__)

@app.route("/api/render")
def render_template():
    user_input = request.args.get("content", "")
    html = "<div>" + str(escape(user_input)) + "</div>"
    return html

@app.route("/api/deserialize", methods=["POST"])
def deserialize_data():
    data = request.form.get("data", "")
    try:
        obj = json.loads(data)
    except (json.JSONDecodeError, ValueError):
        return jsonify({"error": "Invalid JSON data"}), 400
    return jsonify({"result": str(obj)})

@app.route("/api/parse-config", methods=["POST"])
def parse_config():
    config_text = request.form.get("config", "")
    config = yaml.safe_load(config_text)
    return jsonify({"config": config})
