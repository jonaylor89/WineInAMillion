import pandas as pd 
import numpy as np
import time

from bert_serving.server import BertServer
from bert_serving.server.helper import get_run_args,get_args_parser, get_shutdown_parser
from bert_serving.client import BertClient


# df= pd.read_csv("wine-reviews/winemag-data-130k-v2.csv") 
#df= pd.read_csv("../wine-reviews/winemag-data_first150k.csv") 


"""
print(df)
print(df.columns)
wine_types = df['variety'].unique()
# print(wine_types)
print('There are',len(wine_types),'wine types.')
print(df['description'].head())

# mani use this to encode the ngram array bud into vectors
bert_args = get_run_args()
print(bert_args)
server = BertServer(bert_args)
server.start()
time.sleep(20)
"""
bc = BertClient()

print(bc.encode(['First do it', 'then do it right', 'then do it better']))


shut_args = get_shutdown_parser().parse_args(['-ip','localhost','-port','5555','-timeout','5000'])
BertServer.shutdown(shut_args)
