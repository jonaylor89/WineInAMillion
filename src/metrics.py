import pandas as pd 
import numpy as np


df= pd.read_csv("wine-reviews/winemag-data_first150k.csv") 

print(df)
print(df.columns)
wine_types = df['variety'].unique()
# print(wine_types)
print('There are',len(wine_types),'wine types.')
print(df['description'].head())
