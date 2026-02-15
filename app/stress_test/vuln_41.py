from flask import Flask, request, make_response
app = Flask(__name__)
@app.route("/stress41")
def handler_41():
    data = request.args.get("d", "")
    resp = make_response(data)
    resp.headers["Content-Type"] = "text/html"
    return resp
