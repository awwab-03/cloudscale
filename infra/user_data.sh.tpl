#!/bin/bash
# CloudScale app instance bootstrap (rendered by Terraform templatefile; no secrets here).
set -euxo pipefail
exec > >(tee /var/log/cloudscale-userdata.log) 2>&1

dnf install -y python3.12 python3.12-pip unzip

mkdir -p /opt/cloudscale
cd /opt/cloudscale
aws s3 cp "s3://${artifacts_bucket}/app/app-${app_version}.zip" app.zip --region ${region}
rm -rf app
mkdir app
# unzip exits 1 on warnings (e.g. path-separator notices); only fail on real errors (>1)
unzip -q app.zip -d app || [ $? -eq 1 ]

python3.12 -m venv venv
./venv/bin/pip install --no-cache-dir -r app/requirements.txt

# Non-secret config only. DB credentials (Secrets Manager) and the Flask key (SSM) are fetched at runtime by the app.
cat > /etc/cloudscale.env <<'ENVEOF'
AWS_REGION=${region}
AWS_DEFAULT_REGION=${region}
APP_VERSION=${app_version}
DB_HOST=${db_host}
DB_NAME=${db_name}
DB_SECRET_ARN=${db_secret_arn}
UPLOADS_BUCKET=${uploads_bucket}
COGNITO_POOL_ID=${cognito_pool_id}
COGNITO_CLIENT_ID=${cognito_client_id}
CLAIM_TOPIC_ARN=${claim_topic_arn}
SSM_PREFIX=/cloudscale
SAGEMAKER_ENDPOINT=cloudscale-category
BEDROCK_MODEL_ID=us.amazon.nova-micro-v1:0
ENVEOF
chmod 600 /etc/cloudscale.env

useradd --system --home /opt/cloudscale --shell /sbin/nologin cloudscale || true
chown -R cloudscale:cloudscale /opt/cloudscale

cat > /etc/systemd/system/cloudscale.service <<'UNITEOF'
[Unit]
Description=CloudScale Lost and Found (gunicorn)
After=network-online.target
Wants=network-online.target

[Service]
User=cloudscale
EnvironmentFile=/etc/cloudscale.env
WorkingDirectory=/opt/cloudscale/app
ExecStart=/opt/cloudscale/venv/bin/gunicorn --config gunicorn.conf.py app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNITEOF

systemctl daemon-reload
systemctl enable --now cloudscale.service
