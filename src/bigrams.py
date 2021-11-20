import re
from nltk.util import ngrams
import pandas as pd

def bigrams(desc):
    return re.sub(r'[^a-zA-Z0-9\s]', '', desc)

s = pd.read_csv("wine-reviews/winemag-data_first150k.csv")

# s = s.lower()
s["descriptionRegex"] = s["description"]
s["descriptionRegex"].map(bigrams)
print(s['descriptionRegex'].head())

ngramify = lambda x: list(ngrams([token for token in x.split(" ") if token != ""],2))
s['trigrams'] = s['descriptionRegex'].apply(ngramify)
# print(s.head)
# print(s['bigrams'])

#tokens = [token for token in s.split(" ") if token != ""]
# print(s['description'])
#output = list(ngrams(tokens, 3))
#print(output)
