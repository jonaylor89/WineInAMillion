import argparse
import logging
import requests

import boto3
import os
import json
import io
import time
import pandas as pd
from sklearn.externals import joblib
from sklearn.neighbors import NearestNeighbors

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CONTENT_TYPE = 'application/json'

def model_fn(model_dir):
    logger.info('model_fn')
    logger.info(model_dir)
    model = joblib.load(model_dir)
    logger.info(model)
    return model

# Deserialize the Invoke request body into an object we can perform prediction on
def input_fn(serialized_input_data, content_type=CONTENT_TYPE):
    logger.info('Deserializing the input data.')
    if content_type == CONTENT_TYPE:
        data = json.loads(serialized_input_data)
        return data
    raise Exception('Requested unsupported ContentType in content_type: {}'.format(content_type))

# Perform prediction on the deserialized object, with the loaded model
def predict_fn(input_object, model):
    logger.info("Calling model")
    start_time = time.time()
    print(input_object)
    embeddingsVector input_object['embeddings']
    print('embeddings', embeddingsVector)
    neighbors = model.kneighbors(embeddingsVector, 5, return_distance=False)
    print("--- Inference time: %s seconds ---" % (time.time() - start_time))
    return neighbors

# Serialize the prediction result into the desired response content type
def output_fn(prediction, accept):
    logger.info('Serializing the generated output.')
    if accept == 'application/json':
        output = json.dumps({"recommendations": prediction})
        return output
    raise Exception('Requested unsupported ContentType in Accept: {}'.format(content_type))

