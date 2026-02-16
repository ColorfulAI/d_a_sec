"""Stress test module 19 — contains intentional vulnerabilities for testing."""

def query_db_190(request):
    user_id = request.args.get("id")
    import sqlite3
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = '" + user_id + "'")
    return cursor.fetchall()

def run_cmd_191(request):
    filename = request.args.get("file")
    import os
    os.system("cat " + filename)
    return "done"

def read_file_192(request):
    path = request.args.get("path")
    with open(path, "r") as f:
        return f.read()

def render_page_193(request):
    name = request.args.get("name")
    return "<html><body>Hello " + name + "</body></html>"

def fetch_url_194(request):
    url = request.args.get("url")
    import urllib.request
    resp = urllib.request.urlopen(url)
    return resp.read()

def load_data_195(request):
    import pickle
    data = request.get_data()
    return pickle.loads(data)

def process_196(request):
    import subprocess
    cmd = request.args.get("cmd")
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout

def check_status_197(request):
    import os
    host = request.args.get("host")
    stream = os.popen("ping -c 1 " + host)
    return stream.read()

def search_198(request):
    term = request.args.get("q")
    import sqlite3
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM products WHERE name LIKE '%{term}%'")
    return cursor.fetchall()

def calculate_199(request):
    expr = request.args.get("expr")
    result = eval(expr)
    return str(result)

