from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route("/stress82")
def handler_82():
    expr = request.args.get("e", "1+1")
    return jsonify({"result": eval(expr)})
