import os
from flask import Flask, render_template
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

def run():
    port = int(os.getenv("PORT", 8080))  # Railway usa una variable de entorno PORT
    app.run(host="0.0.0.0", port=port)

def start_web():
    thread = Thread(target=run)
    thread.start()
