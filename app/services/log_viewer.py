from flask import Flask, Response, request

app = Flask(__name__)

LOG_FILES = {
    "app": "/var/log/app.log",
    "error": "/var/log/error.log",
    "access": "/var/log/access.log",
}


@app.route("/logs/view")
def view_log():
    log_name = request.args.get("name", "app")
    log_path = LOG_FILES.get(log_name)
    if log_path is None:
        return "Log not found", 404
    with open(log_path) as f:
        return Response(f.read(), mimetype="text/plain")
