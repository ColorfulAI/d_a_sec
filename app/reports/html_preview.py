from flask import Flask, request, make_response

app = Flask(__name__)


@app.route("/preview")
def preview_html():
    user_html = request.args.get("html", "<p>Hello</p>")
    resp = make_response(user_html)
    resp.headers["Content-Type"] = "text/html"
    return resp
