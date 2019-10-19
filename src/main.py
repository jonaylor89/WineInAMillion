#!/usr/bin/env python3

from flask import Flask, request

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "Hello World"


@app.route("/search")
def wine_search():
    term = request.args.get("q", default="", type=str)

    if term == "":
        return {}
    
    


if __name__ == "__main__":
    app.run()
