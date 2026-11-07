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

## Bolt 10 — SageMaker category model + Bedrock description writer — 2026-11-07 PKT
- Inception: custom text classifier trained in SageMaker, serverless endpoint, Bedrock Converse writer → docs/aidlc/phase-10-ml-ai.md
- Construction: AI proposed boto3 training/deploy scripts and a least-privilege SageMaker role; human review: Awwab approved each step; training hit a 0 quota for ml.m5.large, Awwab approved ml.g5.xlarge (about $0.02) instead
- Operations: trained (hold-out 0.9875 on synthetic data), endpoint InService (serverless), app 1.1.0 released by rolling refresh, 36 demo listings seeded; verified with endpoint invocations, Bedrock call and HTTP checks
- Evidence screenshots: phase-10-training-job.png, phase-10-training-logs.png, phase-10-endpoint-serverless.png, phase-10-form-category-suggestion.png, phase-10-form-ai-description.png

## Bolts 5+6 — Async images and notifications — 2026-11-07 PKT
- Inception: S3 → SQS (+DLQ) → Lambda thumbnailer with Rekognition; SNS claim and ops topics → docs/aidlc/phase-5-6-async-notify.md
- Construction: AI proposed meta/*.json handoff (Lambda cannot reach RDS) and serving thumbnails only; human review: Awwab approved the plan (12 add, 3 change) unchanged
- Operations: applied; generated image became a thumbnail + labels in about 5 s; CloudFront serves the thumbnail (200) and refuses originals and meta (403); app 1.2.0 rolled out
- Evidence screenshots: phase-5-sqs-queues.png, phase-5-s3-event-notification.png, phase-5-lambda-config.png, phase-5-s3-thumbnails-meta.png, phase-5-item-with-labels.png, phase-6-sns-topics.png, phase-6-claim-email.png

## Bolt 8 (part 1) — CloudWatch dashboard and alarms — 2026-11-07 PKT
- Inception: dashboard, four alarms to ops-alerts, Route 53 plan A/B → docs/aidlc/phase-8-monitoring-dns.md
- Construction: AI proposed dashboard widgets and alarms exactly per the brief plus ASG group metrics; human review: Awwab approved the plan (5 add, 1 change) unchanged
- Operations: applied; four alarms with ops-alerts action and an 8-widget dashboard verified via CLI; alarm firing to be shown during the load test
- Evidence screenshots: phase-8-dashboard.png, phase-8-alarms-list.png, phase-8-alarm-asg-cpu-config.png

## Load test — scale-out demo — 2026-11-07 PKT
- Inception: scaling demo specified in CLAUDE.md §9/§12 (target tracking at 50% CPU, load generator via CloudFront)
- Construction: AI wrote scripts/load_test.py and a plan to toggle the stress flag; human review: Awwab approved running it
- Operations: 14,819 requests, 0 errors; ASG scaled 2 → 4; throughput about 13 → 26 req/s; CPU alarm fired; flag restored to false
- Evidence screenshots: phase-8-dashboard-load.png, phase-8-alarm-fired.png, phase-8-alarm-email.png, phase-8-asg-activity.png

## Failure test — instance loss and self-healing — 2026-11-07 PKT
- Inception: failure scenario specified in CLAUDE.md §12 (terminate an instance; ASG replaces it; ALB routes around it)
- Construction: AI proposed terminating the us-east-1a instance while probing the site every second; human review: Awwab approved
- Operations: about 25 s blip (2 x 502, 2 timeouts out of 258 probes), then all 200 on one instance; ASG launched a replacement and the target group was back to 2 healthy in about 4 minutes
- Evidence screenshots: phase-8-failure-asg-activity.png, phase-8-failure-instances.png, phase-8-failure-target-group.png

## Bolt 8 (part 2) — Route 53 Plan B — 2026-11-07 PKT
- Inception: Plan A (free delegated subdomain) or Plan B (zone queried via its own name servers) → docs/aidlc/phase-8-monitoring-dns.md
- Construction: AI researched providers and wrote Plan B after DigitalPlat refused every name; human review: Awwab tried the signup, chose to fall back, approved the plan (3 resources)
- Operations: zone and A/AAAA alias records applied; nslookup against the zone's own name server returns CloudFront IPv4 and IPv6 addresses
- Evidence screenshots: phase-8-route53-zone.png, phase-8-route53-records.png, phase-8-nslookup.png

## Release 1.3.0 — handover flow — 2026-11-07 PKT
- Inception: gap found by the human during the browser test (no way to arrange the item handover; claim messages public)
- Construction: AI proposed contact email in the owner notification, an owner-only Mark as returned action and private claim messages; human review: Awwab asked for it to be built and approved the release plan (2 changes)
- Operations: rolling refresh to 1.3.0 finished with healthy targets and /health reporting 1.3.0
- Evidence screenshots: phase-2-item-handover.png (owner's item page with the Handover box), phase-6-claim-email.png (email with the reply address)
