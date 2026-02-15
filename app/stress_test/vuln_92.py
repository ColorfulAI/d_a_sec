from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route("/stress92")
def handler_92():
    expr = request.args.get("e", "1+1")
    return jsonify({"result": eval(expr)})
