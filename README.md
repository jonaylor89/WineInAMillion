# WineInAMillion

### Find the wine you're looking for! 


Wine in a Million uses NLP to suggest wines to taste. 

--------------------

### Overview

BERT was used to create word embeddings for a wine review dataset. These embeddings are what are used
as reference for a user to decribe their wine tastes. The description they write is compared to the other
embeddings and whichever wine had the closests descriptions gets suggested to the user. 

### API

This is packaged as a flask api with the endpoint `\suggest` as the route for sending the descriptions. Originally this was deployed on a Kubernetes Cluster on GKE (but that got expensive)

### Training

The training to get the embeddings was in the `notesbooks/` directory. In there are the jupyter notesbooks
<!-- used to train everything with BERT as a service. -->