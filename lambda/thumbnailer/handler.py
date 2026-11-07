"""SQS-triggered Lambda: thumbnail + Rekognition labels + moderation for uploaded photos.

Event path: S3 ObjectCreated (originals/) -> SQS image-jobs -> this function.
Outputs (same base name as the original):
  thumbnails/<name>.jpg  - 640px JPEG (skipped when the image is flagged by moderation)
  meta/<name>.json       - {"flagged": bool, "labels": [...], "moderation": [...]}
The function is outside the VPC (no DB access), so the web app reads meta/*.json.
"""
import io
import json
import logging
import os
import urllib.parse

import boto3
from PIL import Image, ImageOps

log = logging.getLogger()
log.setLevel(logging.INFO)

s3 = boto3.client("s3")
rekognition = boto3.client("rekognition")

THUMB_MAX = 640
MODERATION_MIN_CONFIDENCE = 60
LABEL_MIN_CONFIDENCE = 70
MAX_LABELS = 8


def make_thumbnail(data):
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((THUMB_MAX, THUMB_MAX))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85, optimize=True)
    return out.getvalue()


def base_name(key):
    name = key.split("/", 1)[1] if "/" in key else key
    return os.path.splitext(name)[0]


def process_object(bucket, key):
    if not key.startswith("originals/"):
        log.info("skipping non-original key %s", key)
        return
    name = base_name(key)
    original = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    thumb = make_thumbnail(original)  # also used for Rekognition (always < 5 MB)

    moderation = rekognition.detect_moderation_labels(
        Image={"Bytes": thumb}, MinConfidence=MODERATION_MIN_CONFIDENCE
    )["ModerationLabels"]
    flagged = len(moderation) > 0
    meta = {"flagged": flagged, "labels": [], "moderation": sorted({m["Name"] for m in moderation})}

    if flagged:
        log.warning("moderation flagged %s: %s", key, meta["moderation"])
    else:
        labels = rekognition.detect_labels(
            Image={"Bytes": thumb}, MaxLabels=MAX_LABELS, MinConfidence=LABEL_MIN_CONFIDENCE
        )["Labels"]
        meta["labels"] = [l["Name"] for l in labels]
        s3.put_object(
            Bucket=bucket, Key=f"thumbnails/{name}.jpg", Body=thumb,
            ContentType="image/jpeg", CacheControl="public, max-age=86400",
        )

    s3.put_object(
        Bucket=bucket, Key=f"meta/{name}.json", Body=json.dumps(meta).encode("utf-8"),
        ContentType="application/json",
    )
    log.info("processed %s -> flagged=%s labels=%s", key, flagged, meta["labels"])


def handler(event, context):
    failures = []
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            if body.get("Event") == "s3:TestEvent":
                continue
            for rec in body.get("Records", []):
                bucket = rec["s3"]["bucket"]["name"]
                key = urllib.parse.unquote_plus(rec["s3"]["object"]["key"])
                process_object(bucket, key)
        except Exception:
            log.exception("failed message %s", record.get("messageId"))
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}
