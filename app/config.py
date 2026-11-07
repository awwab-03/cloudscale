"""Runtime configuration. Non-secret values come from environment variables (written by
user_data); secrets are fetched at runtime from SSM / Secrets Manager, never stored on disk."""
import json
import os
import time

import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "cloudscale")
DB_SECRET_ARN = os.environ.get("DB_SECRET_ARN", "")
UPLOADS_BUCKET = os.environ.get("UPLOADS_BUCKET", "")
COGNITO_POOL_ID = os.environ.get("COGNITO_POOL_ID", "")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")
CLAIM_TOPIC_ARN = os.environ.get("CLAIM_TOPIC_ARN", "")
SSM_PREFIX = os.environ.get("SSM_PREFIX", "/cloudscale")
APP_VERSION = os.environ.get("APP_VERSION", "dev")
SAGEMAKER_ENDPOINT = os.environ.get("SAGEMAKER_ENDPOINT", "")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-micro-v1:0")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
CATEGORIES = [
    "Electronics", "ID/Cards", "Bags", "Keys", "Clothing",
    "Books/Stationery", "Bottles/Accessories", "Other",
]

_cache = {}


def _cached(key, ttl, loader):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    value = loader()
    _cache[key] = (now, value)
    return value


def get_secret_key():
    def load():
        ssm = boto3.client("ssm", region_name=REGION)
        resp = ssm.get_parameter(Name=f"{SSM_PREFIX}/app-secret-key", WithDecryption=True)
        return resp["Parameter"]["Value"]
    return _cached("secret_key", 3600, load)


def get_db_credentials():
    def load():
        sm = boto3.client("secretsmanager", region_name=REGION)
        data = json.loads(sm.get_secret_value(SecretId=DB_SECRET_ARN)["SecretString"])
        return data["username"], data["password"]
    return _cached("db_creds", 300, load)


def stress_enabled():
    def load():
        try:
            ssm = boto3.client("ssm", region_name=REGION)
            resp = ssm.get_parameter(Name=f"{SSM_PREFIX}/enable-stress")
            return resp["Parameter"]["Value"].strip().lower() == "true"
        except Exception:
            return False
    return _cached("stress", 30, load)
