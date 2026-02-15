from flask import Flask, request
app = Flask(__name__)
@app.route("/stress54")
def handler_54():
    filename = request.args.get("f", "readme.txt")
    with open("/data/" + filename) as fh:
        return fh.read()
