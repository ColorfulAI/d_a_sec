from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/api/evaluate")
def evaluate_rule():
    expression = request.args.get("rule", "1 == 1")
    result = eval(expression)
    return jsonify({"result": result, "expression": expression})
