#!/usr/bin/env python3

import pandas as pd

from flask import Flask, request, jsonify

app = Flask(__name__)
df = pd.read_csv("wine-reviews/winemag-data_first150k.csv")


@app.route("/")
def hello_world():
    return "Hello World"


@app.route("/search")
def wine_search():
    term = request.args.get("q", default="", type=str)

    if term == "":
        return jsonify({"matches": []})

    return jsonify({"matches": [item for item in df["variety"] if term in item]})


if __name__ == "__main__":
    app.run()
