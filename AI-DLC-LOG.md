# AI-DLC Log

Each phase is a bolt: Inception → Construction → Operations.

## Bolt 0 — Repo bootstrap — 2026-11-07 PKT
- Inception: goal/requirements/acceptance for repo + safety rails → docs/aidlc/phase-0-bootstrap.md
- Construction: AI proposed gitignore/gitattributes/skeletons and a private `gh` repo; human review: Awwab approved the plan unchanged
- Operations: repo pushed to github.com/awwab-03/cloudscale (private); verified with `gh repo view` and a secret scan
- Evidence screenshots: phase-0-github-repo.png

## Bolt 1 — Networking — 2026-11-07 PKT
- Inception: VPC/subnets/NAT instance/SG requirements and acceptance criteria → docs/aidlc/phase-1-networking.md
- Construction: AI proposed t4g.nano NAT instance; human review: apply hit a Free-plan block, Awwab approved t4g.micro instead (no plan upgrade)
- Operations: applied in two steps (38 + 4 resources); verified via AWS CLI (NAT running, source/dest check off, SSM online, routes and SG rules correct)
- Evidence screenshots: phase-1-vpc-resource-map.png, phase-1-route-tables.png, phase-1-security-groups.png, phase-1-nat-instance.png

## Bolt 3a — S3 buckets — 2026-11-07 PKT
- Inception: uploads and artifacts buckets, lifecycle, versioning, BPA → docs/aidlc/phase-3a-s3-buckets.md
- Construction: AI proposed two buckets with HTTPS-only policies and deferred CloudFront/SQS policies; human review: Awwab approved the plan (12 resources) unchanged
- Operations: applied; verified BPA, versioning, encryption, lifecycle and policy via AWS CLI
- Evidence screenshots: phase-3a-buckets-list.png, phase-3a-uploads-lifecycle.png, phase-3a-uploads-versioning-bpa.png

## Bolt 4 — RDS PostgreSQL — 2026-11-07 PKT
- Inception: private single-AZ Postgres with Secrets Manager password → docs/aidlc/phase-4-rds.md
- Construction: AI proposed db.t4g.micro, gp3 20 GB, managed master password, 1-day backups; human review: Awwab approved the plan (2 resources) unchanged
- Operations: applied; verified available, private, single-AZ, encrypted, correct security group via AWS CLI
- Evidence screenshots: phase-4-rds-config.png, phase-4-rds-connectivity.png, phase-4-secret.png

## Bolt 7 — Cognito + EC2 IAM role — 2026-11-07 PKT
- Inception: Cognito pool/client, SSM secret, least-privilege app role → docs/aidlc/phase-7-identity.md
- Construction: AI proposed a scoped inline policy with one documented `*` (KMS via SSM); human review: Awwab approved the plan (9 resources) unchanged
- Operations: applied; test user signed up, confirmed, authenticated and was deleted via CLI; policy inspected for wildcards
- Evidence screenshots: phase-7-cognito-pool.png, phase-7-cognito-client.png, phase-7-iam-role.png, phase-7-iam-policy-json.png, phase-7-ssm-param.png

## Bolt 2 (+3b) — App, compute and CloudFront — 2026-11-07 PKT
- Inception: Flask app, ASG/ALB, CloudFront with OAC and origin-verify header → docs/aidlc/phase-2-app-compute.md
- Construction: AI proposed the app and stack (12 to add, 1 to change); human review: Awwab approved; two issues found during apply (ASG service-linked role delay, Windows zip backslashes) were diagnosed from instance logs and fixed with Awwab's approval of a second plan
- Operations: 2 healthy instances behind ALB behind CloudFront; /health 200 through CloudFront, ALB unreachable directly, DB connection and migration proven; browser flow pending
- Evidence screenshots: phase-2-site-home.png, phase-2-signup-confirm.png, phase-2-post-item.png, phase-2-item-with-photo.png, phase-2-alb-target-group-healthy.png, phase-2-asg-instances.png, phase-2-cloudfront-distribution.png, phase-2-ec2-instances-private.png
