"""Teardown: deletes the endpoint, all cloudscale-category endpoint configs and models.

Usage: python ml/delete_endpoint.py
"""
import boto3

REGION = "us-east-1"
ENDPOINT = "cloudscale-category"
sm = boto3.client("sagemaker", region_name=REGION)

try:
    sm.delete_endpoint(EndpointName=ENDPOINT)
    print("deleted endpoint", ENDPOINT)
except sm.exceptions.ClientError as exc:
    print("endpoint:", exc.response["Error"]["Message"])

for c in sm.list_endpoint_configs(NameContains="cloudscale-category")["EndpointConfigs"]:
    sm.delete_endpoint_config(EndpointConfigName=c["EndpointConfigName"])
    print("deleted config", c["EndpointConfigName"])
for m in sm.list_models(NameContains="cloudscale-category")["Models"]:
    sm.delete_model(ModelName=m["ModelName"])
    print("deleted model", m["ModelName"])
