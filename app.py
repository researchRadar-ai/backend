# app.py

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/api/hello")
def hello_world():
    return jsonify({"message": "f;;lkj;000;lkfjsalfd, World!"})
