import argparse
import logging
import sagemaker_containers
import requests

import boto3
import os
import json
import io
import time
import pandas as pd
import joblib
from sklearn.neighbors import NearestNeighbors

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CONTENT_TYPE = 'text/plain'

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
        data = [serialized_input_data.decode('utf-8')]
        return data
    raise Exception('Requested unsupported ContentType in content_type: {}'.format(content_type))

# Perform prediction on the deserialized object, with the loaded model
def predict_fn(input_object, model):
    logger.info("Calling model")
    start_time = time.time()
    neighbors = model.kneighbors(input_object, 5, return_distance=False)
    print("--- Inference time: %s seconds ---" % (time.time() - start_time))
    response = neighbors
    return response

# Serialize the prediction result into the desired response content type
def output_fn(prediction, accept):
    logger.info('Serializing the generated output.')
    if accept == 'application/json':
        output = json.dumps(prediction)
        return output
    raise Exception('Requested unsupported ContentType in Accept: {}'.format(content_type))

