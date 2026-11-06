# CloudScale — Campus Lost & Found on AWS

This file is the project brief for Claude Code. Read it fully at the start of every session.

## 1. Context

- **Course:** CS-4075 Cloud Computing, FAST-NUCES Islamabad. Instructor: Dr. Basharat Hussain.
- **Assignment:** "CloudScale" semester project (spec PDF is in `docs/spec/` if present).
- **Group (duo):** Awwab Aamir (22i-0971) and Rayyan Khan (22i-1002). Awwab is doing the hands-on work.
- **DEADLINE: Sunday 8 Nov 2026, 11:59 PM PKT (UTC+5).** Target submission by 10 PM. Speed matters; scope is fixed.
- **Machine:** Windows, PowerShell. Terraform, AWS CLI v2, Git, GitHub CLI, Python 3.12 installed.
- **AWS:** a brand-new account created on 7 Nov 2026, on the Free account plan, $100 credit. Region **us-east-1** for everything. The default CLI profile is an IAM user `cloudscale-deployer`.
- **Alert email:** i220971@nu.edu.pk
- **AWS Budget:** "Cloud Scale", $100/month, alerts at 50%/80% actual and 100% forecasted. It was created on 7 Nov via the console. **Do not recreate it in Terraform.** Reference it in the report.

## 2. Non-negotiable rules (the grading penalties)

1. **Human approval before any change to AWS.** Always use plan mode or show a `terraform plan` summary first. Run `terraform apply`, `destroy`, or any mutating AWS CLI or SDK call only after Awwab explicitly says to apply. This is the AI-DLC "Construction" review and it is graded.
2. **No `AdministratorAccess` and no broad wildcards** on any role or policy you create (−10). Every runtime role (EC2, Lambda, SageMaker) gets only the actions and resource ARNs it needs. Some APIs don't support resource-level permissions (e.g. Rekognition DetectLabels, `cloudwatch:PutMetricData`). Only there use `"Resource": "*"`, and add a comment plus a note in `docs/iam-justification.md`.
3. **No secrets in Git, ever (−10).** Never write access keys into files. Don't hardcode passwords; use the RDS `manage_master_user_password` setting (Secrets Manager) and SSM SecureString for the app secret key. `.gitignore` must cover `*.tfstate*`, `.terraform/`, `*.tfvars` (commit only `*.tfvars.example`), `.env*`, `*.pem`, `build/`, `dist/`, `*.zip`, `__pycache__/`, `.venv/`. Before every commit, scan staged files for `AKIA`, `aws_secret_access_key`, and `password=`.
4. **Incremental commits (−5 otherwise).** Make at least 3 commits per phase (inception / construction / operations). Never make one giant commit.
5. **Cost guardrails.** Use the smallest instance sizes. No NAT Gateway (use a NAT instance). No Multi-AZ RDS. The SageMaker endpoint must be **serverless**. No provisioned capacity anywhere. Tag every resource `Project=CloudScale`. Warn Awwab before creating anything billed hourly that isn't in the plan below.
6. **Free-plan blocks.** If any API returns an error saying the service isn't available on the free plan, STOP and tell Awwab. Do not work around it silently. Upgrading the plan is his decision.
7. Never touch the Budget, the billing settings, or the `cloudscale-deployer` user itself.

## 3. AI-DLC workflow (graded: 8 marks)

Each phase is a "bolt":

1. **Inception:** write `docs/aidlc/phase-N-<name>.md`. It holds the plain-language goal, requirements, acceptance criteria, and open questions. Awwab reviews it.
   Commit: `phase-N(inception): <summary>`
2. **Construction:** propose a plan in plan mode, then write the Terraform and code. Show the `terraform plan` resource summary. Wait for "apply". After approval, apply.
   Commit: `phase-N(construction): <summary>`. Append the approved plan summary to the phase doc under "Construction — approved plan", with "Approved by Awwab Aamir, <time>".
3. **Operations:** verify it works (CLI checks or curl). Append "What was built / decisions / verification / screenshots to take" to the phase doc. Add a dated entry to `AI-DLC-LOG.md` and update the README.
   Commit: `phase-N(operations): <summary>`

`AI-DLC-LOG.md` entry format:

```
## Bolt N — <Phase name> — <date time PKT>
- Inception: <1–2 lines> → docs/aidlc/phase-N-*.md
- Construction: <what the AI proposed>; human review: <what Awwab approved or changed>
- Operations: <what was deployed + how it was verified>
- Evidence screenshots: <list>
```

At the end of each phase, tell Awwab exactly which screenshots to take, saved to `docs/screenshots/phase-N-*.png`. Remind him to blur the account ID and never to show keys.

## 4. Application: Campus Lost & Found

**Users:** students. They sign up and sign in with Cognito. They can post a lost or found item (title, notes, location, date, photo), browse and search items, and claim a found item. When someone claims their item, the item's owner gets an email.

**Stack:** Python 3.12 + Flask + gunicorn, with server-rendered Jinja templates and minimal CSS. No SPA. Use boto3 and psycopg (v3).

**Data model (PostgreSQL):**
- `users(sub PK, email, display_name, created_at)`
- `items(id PK, owner_sub FK, kind lost|found, title, notes, description, category, ml_category, ml_confidence, location, item_date, image_key, labels jsonb, status open|claimed|returned, created_at)`
- `claims(id PK, item_id FK, claimant_sub FK, message, created_at)`

Create these via an idempotent SQL migration that runs on app start.

**Feature → AWS service map.** Every service needs a real reason. This table becomes the report's justification table.

| Feature | Service(s) | Why it's needed |
|---|---|---|
| App backend | EC2 ASG (min2/des2/max4, t3.micro, AL2023) in private subnets + ALB | Stateful web app with DB connections; must survive instance loss and scale with traffic |
| HTTPS entry + image delivery | CloudFront: default behavior → ALB (CachingDisabled, AllViewer origin request policy); `/media/*` → S3 via OAC (cached) | Gives the app free HTTPS on `*.cloudfront.net` (needed for Cognito/password safety, since we have no domain cert); caches photos at the edge |
| Photo storage | S3 `cloudscale-uploads-<acct>`: `originals/`, `thumbnails/`, `meta/`; Block Public Access on; versioning; lifecycle | Uploads must never live on EC2 disk (instances are disposable in an ASG) |
| Relational data | RDS PostgreSQL 16, db.t4g.micro, single-AZ, 20 GB gp3, private DB subnet group, not public | Users, items, and claims are related entities with foreign keys and joins (claims ↔ items ↔ users); search and filter queries |
| Async image processing | S3 event (`originals/` prefix) → SQS `image-jobs` (+ DLQ, maxReceiveCount 3) → Lambda `thumbnailer` | Thumbnailing and image analysis are slow and bursty; must not block the upload request |
| Image labels + moderation (BONUS) | Rekognition DetectLabels + DetectModerationLabels in the Lambda | Auto-tags photos ("wallet", "keys"); hides inappropriate uploads |
| Claim notifications | SNS topic `claim-notifications` with email subscriptions + filter policy on `owner_email` | Owner is emailed when someone claims their item |
| Ops alerts | SNS topic `ops-alerts` → i220971@nu.edu.pk | CloudWatch alarm target |
| Auth | Cognito User Pool, email sign-up + verification, app client without a secret, `ALLOW_USER_PASSWORD_AUTH` + `ALLOW_REFRESH_TOKEN_AUTH`; Flask calls SignUp / ConfirmSignUp / InitiateAuth server-side and verifies the ID token with the pool's JWKS | No hand-rolled auth; avoids the HTTPS callback problem of the Hosted UI |
| Auto-categorize listing | SageMaker: scikit-learn TF-IDF + LogisticRegression text classifier (categories: Electronics, ID/Cards, Bags, Keys, Clothing, Books/Stationery, Bottles/Accessories, Other), trained in a SageMaker training job, deployed to a **serverless inference endpoint** | Custom model trained on our own listing data; predicts the category as the user types or posts |
| AI description writer | Bedrock Runtime Converse API, Amazon Nova Micro (verify the exact model or inference-profile ID in us-east-1; Nova avoids the Anthropic use-case form). "Write description" button turns terse notes into a clear listing description | Generative task a small classifier can't do; SageMaker = our own predictive model, Bedrock = foundation-model generation |
| Monitoring | CloudWatch dashboard + alarms | Required observability |
| Name | Route 53 hosted zone (see §7) | Friendly name |

**Training data:** generate `ml/data/seed_listings.csv` with about 400 realistic, varied, campus-flavored listing titles and notes, labeled by category. Use the same file to seed the app DB so the model is "built on our application data". Be honest about this in the report.

## 5. Network and security design

- VPC `10.20.0.0/16`, AZs us-east-1a and us-east-1b.
  - Public: `10.20.1.0/24`, `10.20.2.0/24`
  - Private app: `10.20.11.0/24`, `10.20.12.0/24`
  - Private DB: `10.20.21.0/24`, `10.20.22.0/24`
- IGW for the public subnets. Run one **NAT instance** (t4g.nano; the fck-nat AMI is fine, or AL2023 with iptables masquerade) in public subnet A, with source/dest check off. The private route tables send `0.0.0.0/0` to the NAT instance's ENI. A single NAT is acceptable for budget reasons; note it in the report as a known single point of failure.
- Add a free **S3 gateway VPC endpoint** for the private route tables (saves NAT traffic).
- Security groups (least privilege, no SSH anywhere; use SSM Session Manager):
  - `alb-sg`: inbound TCP 80 **only from the managed prefix list `com.amazonaws.global.cloudfront.origin-facing`**
  - `app-sg`: inbound 8000 only from `alb-sg`
  - `db-sg`: inbound 5432 only from `app-sg`
  - `nat-sg`: inbound all only from the two private app subnet CIDRs; outbound all
  - Lambda is not in the VPC (it only needs S3, SQS, and Rekognition).
- The ALB checks a custom header `X-Origin-Verify` (a random value set on the CloudFront origin) via a listener rule, and returns 403 otherwise. This is defense in depth.

## 6. Runtime IAM roles (names must start with `cloudscale-`)

- `cloudscale-ec2-app`:
  - `s3:GetObject` on `artifacts bucket/app/*`
  - `s3:PutObject` / `s3:GetObject` / `s3:DeleteObject` on `uploads/originals/*`
  - `s3:GetObject` on `uploads/thumbnails/*` and `uploads/meta/*`
  - `secretsmanager:GetSecretValue` on the RDS secret ARN only
  - `ssm:GetParameter(s)` on `/cloudscale/*`
  - `kms:Decrypt` via the SSM service condition (if needed)
  - `cognito-idp`: only the needed actions on the pool ARN (`AdminGetUser` if used; SignUp/InitiateAuth are public APIs)
  - `sns:Publish` on `claim-notifications`; `sns:Subscribe` on `claim-notifications`
  - `bedrock:InvokeModel` on the specific Nova model / inference-profile ARNs
  - `sagemaker:InvokeEndpoint` on the endpoint ARN
  - AWS managed `AmazonSSMManagedInstanceCore` (for Session Manager) and CloudWatch agent permissions scoped to the log group
- `cloudscale-lambda-thumbnailer`:
  - `sqs:ReceiveMessage` / `DeleteMessage` / `GetQueueAttributes` on `image-jobs`
  - `s3:GetObject` on `originals/*`; `s3:PutObject` on `thumbnails/*` and `meta/*`
  - `rekognition:DetectLabels` / `DetectModerationLabels` (Resource `*`, documented)
  - Logs on its own log group
- `cloudscale-sagemaker-exec`: S3 read/write only on `artifacts bucket/ml/*`, plus ECR pull for the sklearn image and logs.
- The deployer user (`cloudscale-deployer`) is a human deploy identity with PowerUserAccess plus a scoped IAM policy (`cloudscale-*` roles only). Explain this in the report; delete it at teardown.

## 7. DNS (no owned domain)

- **Plan A:** get a free subdomain from a provider that supports **NS delegation** (research which one works today, e.g. DigitalPlat FreeDomain). Create a Route 53 public hosted zone for it and delegate the NS records. Use an ACM certificate (DNS-validated, us-east-1) on CloudFront with an alias record such as `app.<subdomain>` → CloudFront.
- **Plan B (if the subdomain isn't ready by Sunday 12:00):** create the Route 53 public hosted zone anyway, with a record pointing to the CloudFront domain. Demonstrate resolution by querying the zone's own name servers (`nslookup app.<zone> ns-xxx.awsdns-xx.com`). Explain the limitation honestly in the report.

## 8. Storage lifecycle

Versioning is ON for the uploads bucket. Lifecycle rules:
- `originals/`: → STANDARD_IA at 30 days → GLACIER_IR at 90 days
- Noncurrent versions expire after 30 days
- Abort incomplete multipart uploads after 1 day

The report must explain why: photos are rarely viewed after an item is resolved, and versioning protects against accidental overwrite or delete. Set `force_destroy = true` so teardown works.

## 9. Compute, deploy and scaling

- A launch template for AL2023 t3.micro. `user_data` installs Python 3.12 and deps, downloads `s3://<artifacts>/app/app-<version>.zip`, reads config from SSM and Secrets Manager, and runs gunicorn (2 workers) as a systemd service on :8000.
- The health check is `/health`, which returns 200 and does a cheap DB ping.
- Changing the `app_version` variable creates a new launch template version, which triggers an ASG instance refresh (rolling update).
- Scaling: target tracking on ASG average CPU at 50%.
- `/api/stress?ms=300` burns CPU for load testing; it's enabled by an SSM flag.
- `scripts/load_test.py` is an asyncio + httpx load generator that hits `/api/stress` through CloudFront and prints request rate and latency.
- Package scripts are PowerShell: `scripts/package_app.ps1` zips `app/` and uploads it to the artifacts bucket.
- Lambda packaging on Windows: `pip install --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.12 --target build/thumbnailer pillow`, then let Terraform `archive_file` zip it.
- Add a `.gitattributes` with `*.sh text eol=lf` and `*.tpl text eol=lf` so user_data isn't broken by CRLF.

## 10. Monitoring (Phase 8)

- Dashboard `CloudScale`:
  - ASG avg CPU, plus InService instance count
  - ALB RequestCount, TargetResponseTime (p50/p90), HealthyHostCount, HTTPCode_Target_5XX
  - Lambda Invocations / Errors / Duration
  - SQS ApproximateNumberOfMessagesVisible and the DLQ depth
- Alarms → `ops-alerts`:
  - ASG CPU > 70% for 2×5 min
  - ALB target 5xx > 5 in 5 min
  - Lambda Errors ≥ 1
  - DLQ messages ≥ 1

## 11. Repo layout

```
CLAUDE.md  README.md  AI-DLC-LOG.md  .gitignore  .gitattributes
infra/      providers.tf variables.tf network.tf security.tf storage.tf database.tf identity.tf
            compute.tf cdn.tf serverless.tf messaging.tf ml.tf monitoring.tf dns.tf outputs.tf
            user_data.sh.tpl  terraform.tfvars.example
app/        app.py  config.py  db.py  auth.py  aws_clients.py  migrations/001_init.sql
            templates/  static/  requirements.txt  gunicorn.conf.py
lambda/thumbnailer/   handler.py  requirements.txt
ml/         data/seed_listings.csv  train.py (SageMaker SKLearn entry)  launch_training.py
            deploy_endpoint.py  delete_endpoint.py  requirements.txt
scripts/    package_app.ps1  build_lambda.ps1  load_test.py  seed_db.py  teardown.ps1
docs/       aidlc/  screenshots/  architecture.(drawio|png)  iam-justification.md  report/
```

Use Terraform with local state (gitignored). Use provider `hashicorp/aws ~> 5.x` (or the latest stable; verify). Set `default_tags { Project = "CloudScale" }` on the provider.

## 12. Phase order and schedule (PKT)

| # | Bolt | When | Done when |
|---|---|---|---|
| 0 | Repo bootstrap: git init, private GitHub repo `cloudscale`, .gitignore, .gitattributes, README skeleton, AI-DLC-LOG, this file | Sat early | Pushed; Awwab sends the collaborator invite |
| 1 | Networking (VPC, subnets, IGW, NAT instance, routes, S3 endpoint, SGs) | Sat early / morning | Private instance can reach the internet via NAT |
| 3a | S3 buckets (uploads, artifacts), versioning, lifecycle, bucket policies | Sat morning | Buckets exist; BPA on |
| 4 | RDS PostgreSQL private | Sat morning | Available; not publicly accessible |
| 7 | Cognito pool + client; IAM roles for EC2 | Sat midday | Test user can sign up via CLI |
| 2 | App + launch template + ASG + ALB; then 3b CloudFront in front | Sat afternoon | App works end-to-end via the CloudFront URL; sign up / in, post item with photo |
| 5+6 | SQS + Lambda thumbnailer (+ Rekognition) + SNS claim emails + ops topic | Sat evening | Upload → thumbnail and labels appear; claim → owner email |
| 10 | SageMaker training + serverless endpoint + Bedrock description writer, wired into the "post item" form | Sun morning | Category suggestion and AI description work in the app |
| 8 | Route 53, CloudWatch dashboard and alarms | Sun midday | Dashboard populated; alarm fires during load test |
| — | Load test (scale-out to 3–4) + failure test (terminate an instance → ASG replaces it; ALB routes around it) | Sun midday | Screenshots + CloudWatch graphs captured |
| — | Docs: architecture diagram, README (setup/deploy/teardown), iam-justification, report draft, demo script | Sun afternoon | Ready for the PDF |
| — | Submit | Sun ≤ 10 PM | |
| — | Teardown after grading (`scripts/teardown.ps1`: destroy, delete the SageMaker endpoint, model and endpoint config, log groups, deployer keys) + cleanup screenshot | Within 48 h of grading | |

If behind schedule, protect in this order: Phase 2 (10 marks) → Phase 10 (10) → zero-penalty items → everything else → bonus (Rekognition) last.

## 13. Cost estimate (verify current prices; the report must justify sizing)

Roughly $2–3/day while everything runs:
- ALB about $0.55/day
- Public IPv4 about $0.12/day each
- 2× t3.micro
- t4g.nano NAT
- db.t4g.micro RDS
- Secrets Manager secret
- Route 53 zone $0.50/month
- SageMaker training job (one ml.m5.large run of a few minutes) + serverless inference (cents)
- Bedrock Nova Micro (fractions of a cent per call)

Target under $20 total. Remind Awwab to check Billing → Credits daily.

## 14. Deliverables checklist

- [ ] Architecture diagram
- [ ] Source + IaC in the repo
- [ ] Private repo with the instructor added as collaborator (GitHub username TBD, ask Awwab)
- [ ] Report PDF: app description, per-service justification, screenshots of each component, scaling demo, failure demo, Budget + Cost Explorer screenshots, AI-DLC evidence, teardown instructions
- [ ] 5–8 min demo video (Claude writes the script; it must include the failure/scaling scenario)
- [ ] Cleanup screenshot after grading

## 15. Open items

- Instructor / TA GitHub username for the collaborator invite.
- Whether the Free plan blocks SageMaker or Bedrock (Awwab is checking).
- Free subdomain provider for Route 53 (Plan A vs B).
