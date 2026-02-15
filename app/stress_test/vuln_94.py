from flask import Flask, request
app = Flask(__name__)
@app.route("/stress94")
def handler_94():
    filename = request.args.get("f", "readme.txt")
    with open("/data/" + filename) as fh:
        return fh.read()
