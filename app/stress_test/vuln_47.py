from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route("/stress47")
def handler_47():
    expr = request.args.get("e", "1+1")
    return jsonify({"result": eval(expr)})
