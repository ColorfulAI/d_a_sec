from flask import request, Flask, make_response
from markupsafe import escape
import json
import base64
import yaml

app = Flask(__name__)

@app.route("/api/render")
def render_template():
    user_input = request.args.get("content", "")
    html = "<div>" + str(escape(user_input)) + "</div>"
    response = make_response(html)
    response.headers["Content-Type"] = "text/html"
    return response

@app.route("/api/deserialize", methods=["POST"])
def deserialize_data():
    encoded = request.form.get("data", "")
    decoded = base64.b64decode(encoded)
    obj = json.loads(decoded)
    return {"result": str(obj)}

@app.route("/api/parse-config", methods=["POST"])
def parse_config():
    config_text = request.form.get("config", "")
    config = yaml.load(config_text)
    return {"config": config}
