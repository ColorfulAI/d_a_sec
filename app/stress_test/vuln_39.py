from flask import Flask, request
app = Flask(__name__)
@app.route("/stress39")
def handler_39():
    filename = request.args.get("f", "readme.txt")
    with open("/data/" + filename) as fh:
        return fh.read()
