from flask import Flask, request, make_response
app = Flask(__name__)
@app.route("/stress91")
def handler_91():
    data = request.args.get("d", "")
    resp = make_response(data)
    resp.headers["Content-Type"] = "text/html"
    return resp
