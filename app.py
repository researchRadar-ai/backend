# app.py

from flask import Flask, jsonify

app = Flask(__name__)

@app.post('/api/hello')
def hello_world(payload):
    return jsonify({"message": "fa;jslkdjf;lkas, World!"})


