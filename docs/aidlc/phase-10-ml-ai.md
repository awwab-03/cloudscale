# Phase 10 — SageMaker category model and Bedrock description writer

## Inception

### Goal (plain language)
Two smart helpers in the "Post an item" form:
1. **Suggest category** — our own small ML model (trained on our own listing data in SageMaker) predicts the category from the title and notes.
2. **Write description** — a Bedrock foundation model (Amazon Nova Micro) turns terse notes into a clear listing description.

### Requirements
**Data**
- `ml/data/seed_listings.csv`: ~400 campus-flavoured listings (`title,notes,category`), 8 categories, produced by `ml/make_seed.py` with a fixed random seed. The same file trains the model and seeds the app DB. It is synthetic (template-generated), and the report will say so honestly.

**SageMaker**
- `ml/train.py` (SageMaker scikit-learn script mode): TF-IDF + LogisticRegression, holds out 20% to report accuracy, refits on all data, saves `model.joblib`; same file provides `model_fn/input_fn/predict_fn/output_fn` for inference.
- `ml/launch_training.py`: uploads code and data to `artifacts/ml/`, runs a **training job** (`ml.m5.large`, a few minutes, 600 s cap) with the `cloudscale-sagemaker-exec` role.
- `ml/deploy_endpoint.py`: creates model, endpoint config and a **serverless** endpoint `cloudscale-category` (1024 MB, max concurrency 2). `ml/delete_endpoint.py` removes them for teardown.
- Uses boto3 directly with the AWS scikit-learn 1.2-1 container (`683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3`).
- Terraform creates the role `cloudscale-sagemaker-exec`: S3 read/write only on `artifacts/ml/*`, ECR pull on that one repository, logs on `/aws/sagemaker/*`, and `ecr:GetAuthorizationToken` (no resource-level support, `*`, documented).

**Bedrock**
- Converse API, model `us.amazon.nova-micro-v1:0` (verified available in this account, no Free-plan block). The EC2 role already allows `bedrock:InvokeModel` on that profile.

**App wiring (second step, after the endpoint is InService)**
- `POST /api/suggest-category` → SageMaker `InvokeEndpoint`; `POST /api/write-description` → Bedrock Converse. Two buttons in the form call them with `fetch`; the predicted category and confidence are saved into `ml_category` / `ml_confidence`.
- Release as app version 1.1.0 (rolling instance refresh).
- Seed the DB from the CSV (a few demo users/listings) so the site isn't empty.

### Acceptance criteria
- Training job `Completed` with accuracy reported in logs; model artifact in `artifacts/ml/output/`.
- Endpoint `InService`, type serverless (`ServerlessConfig` present, no provisioned instances).
- `invoke-endpoint` with "black Samsung phone near library" returns `Electronics`.
- In the live site, both buttons work.

### Risks / notes
- **Cost:** one `ml.m5.large` training job for ~3–5 minutes (about $0.01); serverless endpoint is pay-per-invocation (cents) with no idle charge; Bedrock Nova Micro is fractions of a cent per call.
- **Free plan:** SageMaker may be blocked on the Free plan. If the API refuses, I stop and report.
- The model is a small baseline trained on synthetic data; accuracy on real user text will be lower. Stated in the report.
- Serverless cold start can take several seconds on the first call; the UI shows a "thinking" state and handles errors.
- Every AWS write (S3 upload, training job, endpoint) happens only after approval.

### Open questions
- None.

## Construction — approved plan (stage 1)
`ml/make_seed.py` + `ml/data/seed_listings.csv` (400 rows), `ml/train.py`, `ml/launch_training.py`, `ml/deploy_endpoint.py`, `ml/delete_endpoint.py`, and Terraform role `cloudscale-sagemaker-exec` (`infra/ml.tf`). Plan: 2 to add, 0 to change, 0 to destroy. Local training check: holdout_accuracy 0.9875 on synthetic data.
Approved by Awwab Aamir, 2026-11-07.
