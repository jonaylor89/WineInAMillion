#!/usr/bin/env python3

import os
import pandas as pd

from flask import Flask, request, jsonify

app = Flask(__name__)
df = pd.read_csv(os.path.join(os.getcwd(), "wine-reviews/winemag-data-130k-v2.csv"))


@app.route("/")
def hello_world():
    return "Hello World"


@app.route("/search")
def wine_search():
    term = request.args.get("q", default="", type=str)

    print("[INFO] search term:", term)

    if term == "":
        return jsonify({"matches": []})

    matches = df[df["variety"].str.contains(term, na=False)]["variety"].tolist()

    return jsonify({"matches": matches})


@app.route("/suggest")
def wine_suggest():

    term = request.args.get("q", default="", type=str)

    if term == "":
        return jsonify({"suggestions": []})

    return jsonify({"suggestions": []})


if __name__ == "__main__":
    app.run()
