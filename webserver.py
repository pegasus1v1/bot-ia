from flask import Flask
from threading import Thread

app = Flask("")
@app.route('/')
def index():
    return "El servidor está en funcionamiento."


def run():
    app.run(host="0.0.0.0", port=os.getenv("PORT", 8000))


def keep_alive():
    t = Thread(target=run)
    t.start()
