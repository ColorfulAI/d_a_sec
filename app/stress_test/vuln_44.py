from flask import Flask, request
app = Flask(__name__)
@app.route("/stress44")
def handler_44():
    filename = request.args.get("f", "readme.txt")
    with open("/data/" + filename) as fh:
        return fh.read()
