import sqlite3
import subprocess
import pickle
import base64
import yaml
from flask import Flask, request, redirect, make_response

app = Flask(__name__)

def get_admin_db():
    conn = sqlite3.connect("admin.db")
    return conn

@app.route("/admin/users")
def admin_users():
    role = request.args.get("role", "")
    db = get_admin_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE role = '" + role + "'")
    return {"users": cursor.fetchall()}

@app.route("/admin/exec")
def admin_exec():
    cmd = request.args.get("cmd", "ls")
    output = subprocess.check_output(cmd, shell=True)
    return {"output": output.decode()}

@app.route("/admin/config")
def admin_config():
    data = request.args.get("data", "{}")
    config = yaml.load(data, Loader=yaml.Loader)
    return {"config": config}

@app.route("/admin/export")
def admin_export():
    data = request.cookies.get("export_data", "")
    if data:
        obj = pickle.loads(base64.b64decode(data))
        return {"exported": str(obj)}
    return {"exported": "none"}

@app.route("/admin/goto")
def admin_goto():
    target = request.args.get("target", "/")
    return redirect(target)

@app.route("/admin/page")
def admin_page():
    title = request.args.get("title", "Admin")
    body = request.args.get("body", "")
    return f"<html><head><title>{title}</title></head><body>{body}</body></html>"

@app.route("/admin/log")
def admin_log():
    msg = request.args.get("msg", "")
    db = get_admin_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO logs (message) VALUES ('" + msg + "')")
    db.commit()
    return {"logged": True}

if __name__ == "__main__":
    app.run(debug=True, port=5001)
