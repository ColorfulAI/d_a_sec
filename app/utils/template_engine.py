import json
import base64
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
    encoded = request.form.get("data", "")
    decoded = base64.b64decode(encoded)
    obj = json.loads(decoded)
    return jsonify({"result": str(obj)})

@app.route("/api/parse-config", methods=["POST"])
def parse_config():
    config_text = request.form.get("config", "")
    config = yaml.safe_load(config_text)
    return jsonify({"config": config})
