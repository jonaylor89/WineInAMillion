import argparse
import logging
import sagemaker_containers
import requests

import boto3
import os
import json
import io
import time
import torch
import pandas as pd
from sentence_transformers import models, losses, SentenceTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# set the constants for the content types
CONTENT_TYPE = 'text/plain'

def model_fn(model_dir):
    logger.info('model_fn')
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(model_dir)
    model = SentenceTransformer(model_dir + '/transformer/')
    logger.info(model)
    return model.to(device)

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
    sentence_embeddings = model.encode(input_object)
    print("--- Inference time: %s seconds ---" % (time.time() - start_time))
    response = sentence_embeddings[0].tolist()
    return response

# Serialize the prediction result into the desired response content type
def output_fn(prediction, accept):
    logger.info('Serializing the generated output.')
    if accept == 'application/json':
        output = json.dumps(prediction)
        return output
    raise Exception('Requested unsupported ContentType in Accept: {}'.format(content_type))

# Create Embeddings
def train_fn(model_dir, train, output_bucket, output_prefix):
    logger.info('Creating embeddings')
    model = model_fn(model_dir)
    df = pd.read_csv(train)
    sentence_embeddings = model.encode(df["clean_desc"].tolist())

    embeddings_map = {
        "embeddings": sentence_embeddings,
    }

    # WARNING/TODO : KNN doesn't accept json as input so this'll need to be changed
    with open('embeddings.json', 'w') as f:
        json.dump(sentence_embeddings, f)


    s3 = boto3.resource('s3')    
    s3.Bucket(output_bucket).upload_file('embeddings.json', f'{output_prefix}embeddings.json')

if __name__ == "__name__":

    parser = argparse.ArgumentParser()

    # Data, model, and output directories
    parser.add_argument('--train', type=str, default=os.environ['SM_CHANNEL_TRAIN'])
    parser.add_argument('--model-dir', type=str, default=os.environ['SM_MODEL_DIR'])
    parser.add_argument('--output-bucket', type=str, default=os.environ['SM_OUTPUT_BUCKET'])
    parser.add_argument('--output-prefix', type=str, default=os.environ['SM_OUTPUT_PREFIX'])

    args, _ = parser.parse_known_args()

    train_fn(args.model_dir, args.train, args.output_bucket, args.output_prefix)

