from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route("/stress7")
def handler_7():
    expr = request.args.get("e", "1+1")
    return jsonify({"result": eval(expr)})
