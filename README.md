
# Wine in a Million

Wine Recommender created with sentence-BERT and NearestNeighbor on AWS SageMaker

Authors: [Zephyr](https://github.com/JZHeadley) and [Johannes](https://jonaylor.xyz)

[Blog Post](https://www.jonaylor.com/blog/create-a-wine-recommender)

-----

## Overview

In the associated jupyter notebook, we'll demonstrate how BERT can be used in tandem with Nearest Neighbors to create a recommendation engine that uses natural language as an input. To do this, we'll take advantage of a dataset of wine reviews located here that contains 130k different reviews of various wines. We'll use BERT to take those wine reviews, convert the reviews into word embeddings (i.e. vectors) and store those embeddings in AWS S3. With the embeddings stored in S3, we will then use that as our dataset for the Nearest Neighbor algorithm which will in turn be able to accept new user input, create an embedding for it, and find the K closest embeddings to that user input. In essence finding the wines that have a review most similar to the input the user provided. 
