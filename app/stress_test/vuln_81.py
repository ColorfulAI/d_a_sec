from flask import Flask, request, make_response
from markupsafe import escape
app = Flask(__name__)
@app.route("/stress81")
def handler_81():
    data = request.args.get("d", "")
    resp = make_response(escape(data))
    resp.headers["Content-Type"] = "text/html"
    return resp
