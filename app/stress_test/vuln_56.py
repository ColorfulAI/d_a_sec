from flask import Flask, request, make_response
app = Flask(__name__)
@app.route("/stress56")
def handler_56():
    data = request.args.get("d", "")
    resp = make_response(data)
    resp.headers["Content-Type"] = "text/html"
    return resp
