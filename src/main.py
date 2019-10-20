#!/usr/bin/env python3

import os
import pandas as pd
import pandas as pd
from bert_serving.client import BertClient
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from string import punctuation 

nltk.download('stopwords')
nltk.download('punkt')
nltk.download('wordnet')

bc = BertClient()

s = pd.read_json('data/clean_embedded.json',orient='records')

s['id']=s['Unnamed: 0']

from flask import Flask, request, jsonify

app = Flask(__name__)
df = pd.read_csv(os.path.join(os.getcwd(), "wine-reviews/winemag-data-130k-v2.csv"))


def clean_data(desc):
    words = stopwords.words('english')
    lower = " ".join([w for w in desc.lower().split() if not w in words])
    punct = ''.join(ch for ch in lower if ch not in punctuation)
    wordnet_lemmatizer = WordNetLemmatizer()

    word_tokens = nltk.word_tokenize(punct)
    lemmatized_word = [wordnet_lemmatizer.lemmatize(word) for word in word_tokens]

    word_joined = " ".join(lemmatized_word)
    
    return word_joined

from scipy import spatial

def cosine_encode(desc):

    cosine_similarity = lambda x, y: 1 - spatial.distance.cosine(x, y)
    similarities = []

    # inputted_sentence = ["dry with a fruity aftertaste"] # this inputted sentence needs to get vectorized
    cmp_sent = bc.encode([clean_data(desc)]) # vectorizing the senetence
    for index, row in s.iterrows():
        similarity = cosine_similarity(cmp_sent,row['embeddings'])
        similarities.append((row['id'],row['title'],similarity))
    # for sentences in s["embeddings"]:
    #     similarity = cosine_similarity(cmp_sent, sentences)
    #     print(similarity)
    #     similarities.append((sentences,similarity))

    similarities = sorted(similarities, key=lambda item: -item[2])
    return similarities



@app.route("/")
def hello_world():
    return "Hello World"


@app.route("/health")
def health():
    return "We live"

@app.route("/search")
def wine_search():
    term = request.args.get("q", default="", type=str)

    print("[INFO] search term:", term)

    if term == "":
        return jsonify({"matches": []})

    matches = df[df["title"].str.contains(term, na=False)]
    matches = df.where((pd.notnull(df)), None).to_dict("records")

    return jsonify({"matches": matches})


@app.route("/search-variety")
def wine_search_variety():
    term = request.args.get("q", default="", type=str)

    print("[INFO] search term:", term)

    if term == "":
        return jsonify({"matches": []})

    matches = df[df["variety"].str.contains(term, na=False)]
    matches = df.where((pd.notnull(df)), None).to_dict("records")

    return jsonify({"matches": matches})

"""
@app.route("/search-unique")
def wine_search_unique():
    term = request.args.get("q", default="", type=str)

    print("[INFO] search term:", term)

    if term == "":
        return jsonify({"matches": []})

    matches = (
        df[df["variety"].str.contains(term, na=False)]["variety"].unique().tolist()
    )

    return jsonify({"matches": matches_with_info})
"""

@app.route("/suggest")
def wine_suggest():

    term = request.args.get("q", default="", type=str)

    if term == "":
        return jsonify({"suggestions": []})

    # matches = df[df["variety"].str.contains(term, na=False)]
    # matches = df.where((pd.notnull(df)), None) 

    # suggestions = get_suggestions(variety)
    blah = clean_data(term)
    similarities = cosine_encode(blah)
    # print(cmp_sent)
    print(similarities[-5:])
    best = similarities[len(similarities)-1]
    print(best)

    best_instance = s.iloc[best[0]]
    print(best_instance)

    # print([w[0] for w in similarities[:10]])
    print(len(best_instance['description']))
    print(best_instance['description'])

    return jsonify({"suggestions": similarities[-5:]})


if __name__ == "__main__":
    app.run()
