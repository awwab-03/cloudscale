"""Uploads code + data to s3://<artifacts>/ml/ and runs a SageMaker training job (boto3, no SDK).

Usage: python ml/launch_training.py
"""
import io
import os
import tarfile
import time

import boto3

REGION = "us-east-1"
IMAGE = "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3"
ROLE_NAME = "cloudscale-sagemaker-exec"
HERE = os.path.dirname(os.path.abspath(__file__))

sts = boto3.client("sts", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)
sm = boto3.client("sagemaker", region_name=REGION)

account = sts.get_caller_identity()["Account"]
bucket = f"cloudscale-artifacts-{account}"
role_arn = f"arn:aws:iam::{account}:role/{ROLE_NAME}"

# 1. source tarball (train.py at the root) and training data
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as tar:
    tar.add(os.path.join(HERE, "train.py"), arcname="train.py")
buf.seek(0)
s3.upload_fileobj(buf, bucket, "ml/code/sourcedir.tar.gz")
s3.upload_file(os.path.join(HERE, "data", "seed_listings.csv"), bucket, "ml/data/seed_listings.csv")
print("uploaded code and data to s3://%s/ml/" % bucket)

# 2. training job
job = "cloudscale-category-" + time.strftime("%Y%m%d-%H%M%S")
sm.create_training_job(
    TrainingJobName=job,
    RoleArn=role_arn,
    AlgorithmSpecification={"TrainingImage": IMAGE, "TrainingInputMode": "File"},
    HyperParameters={
        "sagemaker_program": "train.py",
        "sagemaker_submit_directory": f"s3://{bucket}/ml/code/sourcedir.tar.gz",
        "sagemaker_region": REGION,
    },
    InputDataConfig=[{
        "ChannelName": "train",
        "DataSource": {"S3DataSource": {
            "S3DataType": "S3Prefix", "S3Uri": f"s3://{bucket}/ml/data/",
            "S3DataDistributionType": "FullyReplicated"}},
        "ContentType": "text/csv",
    }],
    OutputDataConfig={"S3OutputPath": f"s3://{bucket}/ml/output/"},
    ResourceConfig={"InstanceType": "ml.m5.large", "InstanceCount": 1, "VolumeSizeInGB": 5},
    StoppingCondition={"MaxRuntimeInSeconds": 600},
    Tags=[{"Key": "Project", "Value": "CloudScale"}],
)
print("started training job", job)

while True:
    d = sm.describe_training_job(TrainingJobName=job)
    status = d["TrainingJobStatus"]
    print(time.strftime("%H:%M:%S"), status, d.get("SecondaryStatus"))
    if status in ("Completed", "Failed", "Stopped"):
        break
    time.sleep(20)

if status != "Completed":
    print("FAILURE:", d.get("FailureReason"))
    raise SystemExit(1)
print("model artifact:", d["ModelArtifacts"]["S3ModelArtifacts"])
print("billable seconds:", d.get("BillableTimeInSeconds"))
print("JOB_NAME=" + job)
