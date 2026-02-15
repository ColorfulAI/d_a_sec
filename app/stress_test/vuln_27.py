from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route("/stress27")
def handler_27():
    expr = request.args.get("e", "1+1")
    return jsonify({"result": eval(expr)})
