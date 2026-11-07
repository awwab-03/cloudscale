import json
import logging
import os
import uuid

import boto3
from botocore import UNSIGNED
from botocore.config import Config

import config

log = logging.getLogger("cloudscale.aws")

_s3 = None
_sns = None
_cognito = None
_sm_runtime = None
_bedrock = None


def s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=config.REGION)
    return _s3


def sns():
    global _sns
    if _sns is None:
        _sns = boto3.client("sns", region_name=config.REGION)
    return _sns


def cognito():
    """SignUp / ConfirmSignUp / InitiateAuth are public APIs: call them unsigned (no IAM needed)."""
    global _cognito
    if _cognito is None:
        _cognito = boto3.client(
            "cognito-idp", region_name=config.REGION, config=Config(signature_version=UNSIGNED)
        )
    return _cognito


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS


def upload_photo(file_storage):
    """Store an uploaded photo under originals/ and return its S3 key (or None)."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("Photo must be a jpg, png, webp or gif image.")
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    key = f"originals/{uuid.uuid4().hex}.{ext}"
    s3().upload_fileobj(
        file_storage.stream,
        config.UPLOADS_BUCKET,
        key,
        ExtraArgs={"ContentType": file_storage.mimetype or f"image/{ext}"},
    )
    return key


def subscribe_owner(email):
    """Email subscription filtered on the owner's address. Best effort."""
    if not config.CLAIM_TOPIC_ARN:
        return
    try:
        sns().subscribe(
            TopicArn=config.CLAIM_TOPIC_ARN,
            Protocol="email",
            Endpoint=email,
            Attributes={"FilterPolicy": f'{{"owner_email": ["{email}"]}}'},
        )
    except Exception as exc:  # topic may not exist yet; never break the user flow
        log.warning("SNS subscribe skipped: %s", exc)


def publish_claim(owner_email, item_title, claimant_name, message):
    if not config.CLAIM_TOPIC_ARN:
        return
    try:
        sns().publish(
            TopicArn=config.CLAIM_TOPIC_ARN,
            Subject="Someone claimed your item on CloudScale",
            Message=(
                f"{claimant_name} claimed your item: {item_title}\n\n"
                f"Message: {message or '(none)'}"
            ),
            MessageAttributes={"owner_email": {"DataType": "String", "StringValue": owner_email}},
        )
    except Exception as exc:
        log.warning("SNS publish skipped: %s", exc)


def sm_runtime():
    global _sm_runtime
    if _sm_runtime is None:
        _sm_runtime = boto3.client("sagemaker-runtime", region_name=config.REGION)
    return _sm_runtime


def bedrock():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client("bedrock-runtime", region_name=config.REGION)
    return _bedrock


def predict_category(title, notes):
    """SageMaker serverless endpoint (our own TF-IDF + LogisticRegression model)."""
    resp = sm_runtime().invoke_endpoint(
        EndpointName=config.SAGEMAKER_ENDPOINT,
        ContentType="application/json",
        Body=json.dumps({"title": title, "notes": notes}),
    )
    return json.loads(resp["Body"].read())[0]


DESCRIPTION_SYSTEM = (
    "You write short, clear descriptions for a campus lost-and-found listing. "
    "Write 2 to 3 plain sentences. Use only the facts given, do not invent details such as "
    "brands, colours or contents, and never include phone numbers or other contact details."
)


def write_description(kind, title, notes, category, location):
    """Bedrock Converse API (Amazon Nova Micro): turn terse notes into a listing description."""
    prompt = (
        f"Listing type: {kind}\nTitle: {title}\nCategory: {category}\n"
        f"Location: {location or 'not given'}\nNotes: {notes or 'none'}\n\n"
        "Write the description."
    )
    resp = bedrock().converse(
        modelId=config.BEDROCK_MODEL_ID,
        system=[{"text": DESCRIPTION_SYSTEM}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 200, "temperature": 0.3},
    )
    return resp["output"]["message"]["content"][0]["text"].strip()
