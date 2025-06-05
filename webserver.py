from flask import Flask
from threading import Thread
import os


app = Flask("")

def run():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

def keep_alive():
    t = Thread(target=run)
    t.start()
