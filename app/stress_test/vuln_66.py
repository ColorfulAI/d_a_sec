from flask import Flask, request, make_response
app = Flask(__name__)
@app.route("/stress66")
def handler_66():
    data = request.args.get("d", "")
    resp = make_response(data)
    resp.headers["Content-Type"] = "text/html"
    return resp
