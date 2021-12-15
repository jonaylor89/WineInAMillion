import argparse
import logging
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
CONTENT_TYPE = "application/json"


def model_fn(model_dir):
    logger.info("model_fn")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(model_dir)
    model = SentenceTransformer(model_dir + "/transformer/")
    logger.info(model)
    return model.to(device)


# Deserialize the Invoke request body into an object we can perform prediction on
def input_fn(serialized_input_data, content_type=CONTENT_TYPE):
    logger.info("Deserializing the input data.")
    print(serialized_input_data)
    if content_type == CONTENT_TYPE:
        data = json.loads(serialized_input_data)
        return data
    raise Exception(
        "Requested unsupported ContentType in content_type: {}".format(content_type)
    )


# Perform prediction on the deserialized object, with the loaded model
def predict_fn(input_object, model):
    logger.info("Calling model")
    start_time = time.time()
    print(input_object)
    sentenceToEncode = input_object["data"]
    print("encoding", sentenceToEncode)
    sentence_embeddings = model.encode(sentenceToEncode)
    print("--- Inference time: %s seconds ---" % (time.time() - start_time))
    print(sentence_embeddings.shape)
    response = sentence_embeddings.tolist()
    return response


# Serialize the prediction result into the desired response content type
def output_fn(prediction, accept):
    logger.info("Serializing the generated output.")
    if accept == "application/json":
        output = json.dumps({"embeddings": prediction})
        return output
    raise Exception(
        "Requested unsupported ContentType in Accept: {}".format(content_type)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # Sagemaker specific arguments. Defaults are set in the environment variables.
    parser.add_argument("--output-data-dir", type=str)
    parser.add_argument("--model-dir", type=str, default=os.environ["SM_MODEL_DIR"])
    parser.add_argument("--train", type=str, default=os.environ["SM_CHANNEL_TRAIN"])

    args = parser.parse_args()

    model_name = 'sentence-transformers/all-MiniLM-L6-v2'

    saved_model_dir = 'transformer'
    if not os.path.isdir(saved_model_dir):
        os.makedirs(saved_model_dir)

    model = SentenceTransformer(model_name)
    model.save(args.model_dir)

    # Load the training data into a Pandas dataframe and make sure it is in the appropriate format
    raw_data = pd.read_csv(f"{args.train}/dataset.csv")

    embeddings = []
    for i in range(0, len(raw_data["clean_desc"]) - 1):
        vector = model.encode([raw_data["clean_desc"][i]])
        embeddings.append(vector)

    embeddings_flattened = list(map(lambda x: x[0], embeddings))
    embeddings_df = pd.DataFrame(embeddings_flattened)
    embeddings_df = embeddings_df[:-1]

    # Save to output data dir
    embeddings_df.to_csv(f"{args.output_data_dir}/embeddings.csv")
