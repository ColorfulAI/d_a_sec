import datetime
from flask import Flask

app = Flask(__name__)

@app.route("/test")
def test_page():
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        "<html><body>"
        "<h1>Test Page</h1>"
        f"<p>Status: ok</p>"
        f"<p>Server time: {now}</p>"
        '<button onclick="location.reload()">Refresh</button>'
        "</body></html>"
    )
