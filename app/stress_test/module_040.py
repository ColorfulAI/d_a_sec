"""Stress test module 40 — contains intentional vulnerabilities for testing."""

def query_db_400(request):
    user_id = request.args.get("id")
    import sqlite3
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = '" + user_id + "'")
    return cursor.fetchall()

def run_cmd_401(request):
    filename = request.args.get("file")
    import os
    os.system("cat " + filename)
    return "done"

def read_file_402(request):
    path = request.args.get("path")
    with open(path, "r") as f:
        return f.read()

def render_page_403(request):
    name = request.args.get("name")
    return "<html><body>Hello " + name + "</body></html>"

def fetch_url_404(request):
    url = request.args.get("url")
    import urllib.request
    resp = urllib.request.urlopen(url)
    return resp.read()

def load_data_405(request):
    import pickle
    data = request.get_data()
    return pickle.loads(data)

def process_406(request):
    import subprocess
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

def check_status_407(request):
    import os
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

def search_408(request):
    term = request.args.get("q")
    import sqlite3
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM products WHERE name LIKE '%{term}%'")
    return cursor.fetchall()

def calculate_409(request):
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)

