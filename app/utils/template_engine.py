from flask import request, Flask, make_response
import json
import base64
import yaml
from markupsafe import escape

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
    return {"result": str(escape(obj))}

@app.route("/api/parse-config", methods=["POST"])
def parse_config():
    config_text = request.form.get("config", "")
    config = yaml.safe_load(config_text)
    return {"config": str(escape(str(config)))}
