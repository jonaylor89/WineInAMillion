import argparse
import logging
import requests

import boto3
import os
import json
import io
import time
import pandas as pd
import joblib
from sklearn.neighbors import NearestNeighbors
import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CONTENT_TYPE = "application/json"


bucket = "wineinamillion"
prefix = "data/"
filename = "winemag-data-130k-v2.csv"

assert bucket != "<S3_BUCKET>"
assert prefix != "<S3_KEY_PREFIX>"
assert filename != "<DATASET_FILENAME>"

# Read the dataset into memory.  This is generally bad practice and in a production environment we'd use a real database to reference against
raw_data_location = f"s3://{bucket}/{prefix}raw/{filename}"
df = pd.read_csv(raw_data_location)

def model_fn(model_dir):
    logger.info("model_fn")
    logger.info(model_dir)
    model = joblib.load(model_dir + "/model.joblib")
    logger.info(model)
    return model


# Deserialize the Invoke request body into an object we can perform prediction on
def input_fn(serialized_input_data, content_type=CONTENT_TYPE):
    logger.info("Deserializing the input data.")
    if content_type == CONTENT_TYPE:
        data = json.loads(serialized_input_data)
        return data
    raise Exception(
        "Requested unsupported ContentType in content_type: {}".format(content_type)
    )


def mergeWineDistances(idx,distance):
    wine = df.iloc[idx]
    wine['distance'] = distance
    return wine

# Perform prediction on the deserialized object, with the loaded model
def predict_fn(input_object, model):
    logger.info("Calling model")
    start_time = time.time()
    print(input_object)

    try:
        embeddingsVector = [input_object["embeddings"]]

        kneighbors = 5
        if "kneighbors" in input_object.keys():
            kneighbors = input_object["kneighbors"]

        print(f"k neighbors {kneighbors}")
        distances, neighbors = model.kneighbors(
            embeddingsVector, kneighbors, return_distance=True
        )
        print("--- Inference time: %s seconds ---" % (time.time() - start_time))
        print(f"neighbors {neighbors}")
        print(f"distances {distances}")
        result = list(map(mergeWineDistances, neighbors[0],distances[0]))
        print(f"zipped neighbors {pd.DataFrame(result).to_json(orient='records')}")
        
        return pd.DataFrame(result).to_json(orient='records')

    except Exception as e:
        print(e)
        return []


# Serialize the prediction result into the desired response content type
def output_fn(prediction, accept):
    logger.info("Serializing the generated output.")
    if accept == "application/json":
        output = json.dumps({"recommendations": prediction})
        return output
    raise Exception(
        "Requested unsupported ContentType in Accept: {}".format(content_type)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # Hyperparameters are described here.
    parser.add_argument("--n_neighbors", type=int, default=10)
    parser.add_argument("--metric", type=str, default="cosine")

    # Sagemaker specific arguments. Defaults are set in the environment variables.
    parser.add_argument("--output-data-dir", type=str)
    parser.add_argument("--model-dir", type=str, default=os.environ["SM_MODEL_DIR"])
    parser.add_argument("--train", type=str, default=os.environ["SM_CHANNEL_TRAIN"])

    args = parser.parse_args()

    # Load the training data into a Pandas dataframe and make sure it is in the appropriate format
    embeddings = pd.read_csv(
        os.path.join(args.train, "embeddings.csv.tar.gz"),
        compression="gzip",
        index_col=False,
        header=None,
    )

    # Supply the hyperparameters of the nearest neighbors model
    n_neighbors = args.n_neighbors
    metric = args.metric

    # Now, fit the nearest neighbors model
    nn = NearestNeighbors(n_neighbors=n_neighbors, metric=metric)
    model_nn = nn.fit(embeddings)
    print("model has been fitted")

    # Save the model to the output location in S3
    joblib.dump(model_nn, os.path.join(args.model_dir, "model.joblib"))
