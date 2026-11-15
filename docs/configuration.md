# Configuration reference

The Flask app reads all non-secret settings from environment variables (written to
`/etc/cloudscale.env` by `infra/user_data.sh.tpl` on each instance). Secrets are never stored on disk;
they are fetched at runtime from SSM Parameter Store and Secrets Manager (see `app/config.py`).

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `AWS_REGION` | `us-east-1` | Region for all boto3 clients |
| `DB_HOST` | `localhost` | RDS PostgreSQL endpoint |
| `DB_NAME` | `cloudscale` | Database name |
| `DB_SECRET_ARN` | (empty) | Secrets Manager secret holding the DB username and password |
| `UPLOADS_BUCKET` | (empty) | S3 bucket for item photos and thumbnails |
| `COGNITO_POOL_ID` | (empty) | Cognito user pool ID |
| `COGNITO_CLIENT_ID` | (empty) | Cognito app client ID |
| `CLAIM_TOPIC_ARN` | (empty) | SNS topic used for claim notification emails |
| `SSM_PREFIX` | `/cloudscale` | Prefix for SSM parameters |
| `APP_VERSION` | `dev` | Version string shown in the footer and `/health` |
| `SAGEMAKER_ENDPOINT` | (empty) | Serverless endpoint for category suggestion |
| `BEDROCK_MODEL_ID` | `us.amazon.nova-micro-v1:0` | Bedrock model for the description writer |

## Secrets and runtime flags (not environment variables)

| Name | Store | Cache TTL | Purpose |
|---|---|---|---|
| `<SSM_PREFIX>/app-secret-key` | SSM (SecureString) | 1 hour | Flask session signing key |
| `DB_SECRET_ARN` secret | Secrets Manager | 5 minutes | Database credentials |
| `<SSM_PREFIX>/enable-stress` | SSM (String) | 30 seconds | Enables the `/stress` CPU endpoint for the load test |

The short TTL on `enable-stress` is why the load test starts and stops within about half a minute of
changing the parameter.

## Upload limits and categories

- Maximum upload size: 5 MiB (`MAX_UPLOAD_BYTES`), larger requests get the "too large" error page.
- Allowed image types: `jpg`, `jpeg`, `png`, `webp`, `gif`.
- Categories: Electronics, ID/Cards, Bags, Keys, Clothing, Books/Stationery, Bottles/Accessories, Other.
  The SageMaker model in `ml/train.py` is trained on the same label set, so changing one means
  changing the other.
