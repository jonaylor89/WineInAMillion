import re
from nltk.util import ngrams
import pandas as pd
# import metrics
from progress.bar import ChargingBar

def trigrams(desc):
    return re.sub(r'[^a-zA-Z0-9\s]', '', desc)

#s = pd.read_csv("../wine-reviews/winemag-data_first150k.csv")
s = pd.read_csv("wine-reviews/winemag-data-130k-v2.csv") 

print(s.columns)
# s = s.lower()
# s["description"].map(trigrams)
# print(s['description'].head())

# ngramify = lambda x: list(ngrams([token for token in x.split(" ") if token != ""],3))
# s['trigrams'] = s['description'].apply(ngramify)
# print(s.head)
# print(s['trigrams'])
print(s)


#tokens = [token for token in s.split(" ") if token != ""]
# print(s['description'])
#output = list(ngrams(tokens, 3))
#print(output)

"""
bert_args = get_run_args()
print(bert_args)
server = bertServer(bert_args)
server.start()
time.sleep(20)
"""
from bert_serving.client import BertClient
print("HOLA?")
s=s.head(10000)
print(len(s))
print(s)
bc = BertClient()
print("connected")
bar = ChargingBar('Embedding\t\t\t\t', max=len(s))
def encodings(description):
    bar.next()
    return bc.encode([description])
# encodings = lambda x: bc.encode([x]); bar.next()
s['embeddings'] = s['description'].apply(encodings)

bar.finish()
print(s)
s.to_json('data/embedded.json',orient='records')