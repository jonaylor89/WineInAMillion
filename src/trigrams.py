import re
from nltk.util import ngrams
import pandas as pd

def trigrams(desc):
    return re.sub(r'[^a-zA-Z0-9\s]', '', desc)

s = pd.read_csv("wine-reviews/winemag-data_first150k.csv")

# s = s.lower()
s["description"].map(trigrams)
print(s['description'].head())

ngramify = lambda x: list(ngrams([token for token in x.split(" ") if token != ""],3))
s['trigrams'] = s['description'].apply(ngramify)
print(s.head)
print(s['trigrams'])
print(s)
#tokens = [token for token in s.split(" ") if token != ""]
# print(s['description'])
#output = list(ngrams(tokens, 3))
#print(output)
