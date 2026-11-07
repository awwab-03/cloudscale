"""Creates a SageMaker model + serverless endpoint config + endpoint `cloudscale-category`.

Usage: python ml/deploy_endpoint.py <training-job-name>
"""
import sys
import time

import boto3

REGION = "us-east-1"
IMAGE = "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3"
ROLE_NAME = "cloudscale-sagemaker-exec"
ENDPOINT = "cloudscale-category"  # fixed: the EC2 role's InvokeEndpoint permission names this endpoint

if len(sys.argv) != 2:
    raise SystemExit("usage: python ml/deploy_endpoint.py <training-job-name>")
job = sys.argv[1]

sts = boto3.client("sts", region_name=REGION)
sm = boto3.client("sagemaker", region_name=REGION)
account = sts.get_caller_identity()["Account"]
bucket = f"cloudscale-artifacts-{account}"
role_arn = f"arn:aws:iam::{account}:role/{ROLE_NAME}"
tags = [{"Key": "Project", "Value": "CloudScale"}]

artifact = sm.describe_training_job(TrainingJobName=job)["ModelArtifacts"]["S3ModelArtifacts"]
stamp = time.strftime("%Y%m%d-%H%M%S")
model_name = f"cloudscale-category-model-{stamp}"
config_name = f"cloudscale-category-config-{stamp}"

sm.create_model(
    ModelName=model_name,
    ExecutionRoleArn=role_arn,
    PrimaryContainer={
        "Image": IMAGE,
        "ModelDataUrl": artifact,
        "Environment": {
            "SAGEMAKER_PROGRAM": "train.py",
            "SAGEMAKER_SUBMIT_DIRECTORY": f"s3://{bucket}/ml/code/sourcedir.tar.gz",
            "SAGEMAKER_REGION": REGION,
        },
    },
    Tags=tags,
)
sm.create_endpoint_config(
    EndpointConfigName=config_name,
    ProductionVariants=[{
        "VariantName": "AllTraffic",
        "ModelName": model_name,
        "ServerlessConfig": {"MemorySizeInMB": 1024, "MaxConcurrency": 2},  # serverless: no idle instance
    }],
    Tags=tags,
)
try:
    sm.describe_endpoint(EndpointName=ENDPOINT)
    sm.update_endpoint(EndpointName=ENDPOINT, EndpointConfigName=config_name)
    print("updating existing endpoint", ENDPOINT)
except sm.exceptions.ClientError:
    sm.create_endpoint(EndpointName=ENDPOINT, EndpointConfigName=config_name, Tags=tags)
    print("creating endpoint", ENDPOINT)

while True:
    d = sm.describe_endpoint(EndpointName=ENDPOINT)
    print(time.strftime("%H:%M:%S"), d["EndpointStatus"])
    if d["EndpointStatus"] in ("InService", "Failed"):
        break
    time.sleep(20)
if d["EndpointStatus"] != "InService":
    print("FAILURE:", d.get("FailureReason"))
    raise SystemExit(1)
print("endpoint InService; serverless config:", d["ProductionVariants"][0].get("CurrentServerlessConfig"))
