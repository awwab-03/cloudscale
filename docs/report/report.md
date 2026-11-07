# CloudScale: Campus Lost & Found on AWS

**Course:** CS-4075 Cloud Computing, FAST-NUCES Islamabad. **Instructor:** Dr. Basharat Hussain.
**Team:** Awwab Aamir (22i-0971), Rayyan Khan (22i-1002). **Region:** us-east-1.
**Repository (private, instructor added as collaborator):** <https://github.com/awwab-03/cloudscale>  *(invite sent to `basharathussain` on 2026-11-07; confirm it has been accepted before submitting)*

> Items in [square brackets] are for the team to fill in or confirm before exporting to PDF
> (screenshots, final cost figures, Rayyan's contribution).

---

## 1. Application description

CloudScale is a campus Lost & Found website. Students sign up with their email, post a lost or found item (title, notes,
location, date, photo), browse and search the listings, and claim a found item. The item's owner is emailed when someone
claims it. Behind the scenes, uploaded photos are resized, tagged and moderated asynchronously, and two AI helpers on the post form
suggest a category and write a clean description from terse notes.

It is a server-rendered Python 3.12 / Flask application (gunicorn, Jinja templates, no single-page app) using boto3 and
psycopg 3. Data model (PostgreSQL): `users`, `items` (with `category`, `ml_category`, `ml_confidence`, `labels` JSONB, `image_key`,
`status`), and `claims`. The schema is created by an idempotent SQL migration that runs when the app starts.

## 2. Architecture

![Architecture diagram](../architecture.png)

Request path: browser, then CloudFront (HTTPS), then an Application Load Balancer, then an Auto Scaling group of `t3.micro`
instances in private subnets, which talk to RDS PostgreSQL (private DB subnets), S3, Cognito, SageMaker, Bedrock and SNS.
Photos are delivered from S3 through CloudFront, only as thumbnails. A single NAT instance gives the private subnets outbound
internet access, and a free S3 gateway endpoint keeps S3 traffic off the NAT.

Network: VPC `10.20.0.0/16` over two AZs, with public (`10.20.1-2.0/24`), private-app (`10.20.11-12.0/24`) and private-DB
(`10.20.21-22.0/24`) subnets. Security groups chain: `alb-sg` accepts port 80 only from CloudFront's managed prefix list,
`app-sg` accepts 8000 only from `alb-sg`, `db-sg` accepts 5432 only from `app-sg`. There is no SSH anywhere (Session Manager only).
The ALB additionally returns 403 unless the secret header `X-Origin-Verify` (set by CloudFront) matches.

## 3. Service choices and justification

| Feature | AWS service | Why this service (and not something simpler) |
|---|---|---|
| App backend | EC2 Auto Scaling group (min 2, desired 2, max 4, `t3.micro`) + ALB | Stateful web app holding DB connections; the group replaces failed instances and scales out under load. `t3.micro` is the smallest size that runs Flask comfortably. |
| HTTPS and image delivery | CloudFront (default behaviour to ALB, `/media/*` to S3 via OAC) | We have no domain certificate, and CloudFront gives HTTPS on `*.cloudfront.net` (needed so Cognito passwords are not sent in clear text). It also caches thumbnails at the edge. |
| Photo storage | S3 (versioned, Block Public Access, lifecycle) | Uploads must not live on EC2 disks because instances are disposable. |
| Relational data | RDS PostgreSQL 16, `db.t4g.micro`, single-AZ, private | Users, items and claims are related entities with foreign keys, joins and filtered search, which is a natural relational fit. NoSQL would make the claims-to-items-to-users joins awkward. Single-AZ is a deliberate cost decision. |
| Async image work | S3 event, SQS `image-jobs` (+ DLQ), Lambda | Thumbnailing and image analysis are slow and bursty; the upload request must not wait. SQS buffers bursts and retries; the DLQ catches poison messages after 3 tries. |
| Image labels and moderation (bonus) | Rekognition `DetectLabels`, `DetectModerationLabels` | Tags photos automatically and hides inappropriate uploads. Flagged photos never get a thumbnail, so they are never shown. |
| Claim notifications | SNS topic with email subscriptions, filter policy on `owner_email` | Fan-out and email delivery without running a mail server; the filter means only the owner is emailed. |
| Ops alerts | SNS `ops-alerts` | Target for CloudWatch alarms. |
| Authentication | Cognito user pool (email sign-up and verification) | No hand-rolled password handling. The Flask app calls SignUp, ConfirmSignUp and InitiateAuth server-side and verifies the ID token against the pool's JWKS, which avoids the HTTPS-callback requirement of the hosted UI. |
| Category suggestion | SageMaker: scikit-learn TF-IDF + logistic regression, trained in a SageMaker training job, **serverless** endpoint | A small custom model trained on our own listing data. A serverless endpoint has no idle cost and scales to zero, which fits a low-traffic app. |
| Description writer | Bedrock Converse API, Amazon Nova Micro | A generative task a small classifier cannot do. SageMaker is our own predictive model; Bedrock is a foundation model. Nova Micro is cheap and needs no use-case form. |
| Monitoring | CloudWatch dashboard and four alarms to SNS | Required observability (CPU, 5xx, Lambda errors, DLQ depth). |
| DNS | Route 53 hosted zone with alias records to CloudFront | Friendly name for the app (see limitation in section 10). |
| IaC | Terraform, local state | Repeatable, reviewable infrastructure; the plan output is the human-approval gate. |

**Storage lifecycle:** versioning is on for the uploads bucket. `originals/` moves to STANDARD_IA after 30 days and GLACIER_IR after
90 days; noncurrent versions expire after 30 days; incomplete multipart uploads abort after 1 day. Photos are rarely viewed once an item
is resolved, and versioning protects against accidental overwrite or delete. S3 does not transition objects under 128 KB, so small photos may
stay in STANDARD.

**Why a NAT instance and not a NAT Gateway:** a gateway costs about $1 a day; a `t4g.micro` instance costs about $0.20 a day. The price of that choice is a
single point of failure (one instance in one AZ).

**Training data (honest note):** `ml/data/seed_listings.csv` has 400 listings that a script generated from templates (8 categories x 50). The same file trains the model and seeds
demo data in the app database, so the model is built on the application's own data shape, but the data is synthetic, not collected from real users.

## 4. Evidence per component

[Insert the screenshots listed in each `docs/aidlc/phase-*.md` "Screenshots to take" list. One or two per component is enough.]

| Component | Figure | File |
|---|---|---|
| VPC and subnets | Fig. 1 | `phase-1-vpc-resource-map.png` |
| Route tables and security groups | Fig. 2 | `phase-1-route-tables.png`, `phase-1-security-groups.png` |
| S3 buckets, versioning, lifecycle | Fig. 3 | `phase-3a-buckets-list.png`, `phase-3a-uploads-lifecycle.png` |
| RDS (private, single-AZ) | Fig. 4 | `phase-4-rds-config.png`, `phase-4-rds-connectivity.png` |
| Cognito and IAM role | Fig. 5 | `phase-7-cognito-pool.png`, `phase-7-iam-policy-json.png` |
| Site, ALB, ASG, CloudFront | Fig. 6 | `phase-2-site-home.png`, `phase-2-alb-target-group-healthy.png`, `phase-2-asg-instances.png` |
| Async pipeline (SQS, Lambda, S3 outputs) | Fig. 7 | `phase-5-sqs-queues.png`, `phase-5-lambda-config.png`, `phase-5-s3-thumbnails-meta.png` |
| Notifications (SNS, claim email) | Fig. 8 | `phase-6-sns-topics.png`, `phase-6-claim-email.png` |
| SageMaker training and serverless endpoint | Fig. 9 | `phase-10-training-job.png`, `phase-10-endpoint-serverless.png` |
| AI helpers in the form | Fig. 10 | `phase-10-form-category-suggestion.png`, `phase-10-form-ai-description.png` |
| CloudWatch dashboard and alarms | Fig. 11 | `phase-8-dashboard.png`, `phase-8-alarms-list.png` |
| Route 53 | Fig. 12 | `phase-8-route53-zone.png`, `phase-8-nslookup.png` |

## 5. Scaling-policy demonstration

**Policy:** ASG target tracking on average CPU at 50% (min 2, max 4). **Test:** the app has a CPU-burning endpoint (`/api/stress?ms=300`) that is
enabled by an SSM flag. `scripts/load_test.py` (asyncio + httpx) sent 40 concurrent requests through CloudFront for 14 minutes.

| | 2 instances | 4 instances |
|---|---|---|
| Throughput | about 13 requests/s | about 26 requests/s |
| Median latency | about 3.0 s | about 1.5 s |
| p90 latency | about 3.4 s | about 2.1 s |
| Group CPU | about 98% | about 98% (read while the new instances were still warming up) |

14,819 requests were served with **0 errors**. The target-tracking alarm triggered the scale-out from 2 to 4 instances, and the
`cloudscale-asg-cpu-high` alarm (average CPU above 70% for two 5-minute periods) moved to ALARM and emailed `ops-alerts`.
Each request burns 300 ms of CPU on purpose, so absolute latency is high; the point is that doubling capacity doubled throughput and halved latency.
The group scaled back to 2 instances after the load stopped.
[Figures: `phase-8-dashboard-load.png`, `phase-8-alarm-fired.png`, `phase-8-alarm-email.png`, `phase-8-asg-activity.png`, `phase-8-asg-4-instances.png`.]

## 6. Failure demonstration

With two healthy instances (one per AZ) we terminated the us-east-1a instance while probing the site once a second (258 probes over 9 minutes).
**254 requests returned 200.** The four failures (two 502s and two 5-second timeouts) all happened within about 25 seconds of the termination,
before the ALB stopped sending traffic to the dead target. After that the site was served by the remaining instance without errors. The Auto Scaling group
launched a replacement in us-east-1a and the target group was back to two healthy targets about four minutes after the termination, with no manual action.
So an instance loss is visible as a short blip but not as an outage.
[Figures: `phase-8-failure-asg-activity.png`, `phase-8-failure-instances.png`, `phase-8-failure-target-group.png`.]

## 7. Security and IAM

- No `AdministratorAccess` and no wildcard actions on any role we created. Every statement is scoped to specific ARNs; the only `Resource: "*"` statements are for APIs that
  do not support resource-level permissions: Rekognition detect calls, `ecr:GetAuthorizationToken`, and `kms:Decrypt` restricted to calls made through SSM. Each is listed with its reason in `docs/iam-justification.md`.
- Runtime roles: `cloudscale-ec2-app`, `cloudscale-lambda-thumbnailer`, `cloudscale-sagemaker-exec` (plus a minimal SSM-only role for the NAT instance).
- The deployer is an IAM user with PowerUserAccess plus a scoped IAM policy for `cloudscale-*` roles only. It is a human deploy identity that is deleted at teardown.
- Secrets: the RDS master password is generated and held by RDS in Secrets Manager (never in code, state output or Git); the Flask secret key is an SSM SecureString;
  the app reads both at runtime. `.gitignore` covers state, `*.tfvars`, `.env*` and keys, and a secret scan ran before each commit.
- Photos: Block Public Access on both buckets, HTTPS-only bucket policies, and CloudFront may read only `thumbnails/*`.

## 8. Cost control

An AWS Budget named "Cloud Scale" ($100/month, alerts at 50% and 80% actual and 100% forecast, to the team's email) was created on day one, before any other resource.
Small sizes everywhere: `t3.micro` app instances, `t4g.micro` NAT instance (no NAT Gateway), `db.t4g.micro` single-AZ RDS, and a serverless SageMaker endpoint. Every resource is tagged `Project=CloudScale`.

| Item | Estimated cost |
|---|---|
| ALB + its public IPv4 addresses | about $0.8/day |
| 2 x `t3.micro` | about $0.5/day (more while scaled out) |
| RDS `db.t4g.micro` + 20 GB | about $0.5/day |
| NAT instance + Elastic IP | about $0.3/day |
| SageMaker training (one job, 74 billable seconds) | about $0.02 total |
| Everything else (S3, Lambda, SQS, SNS, Cognito, CloudWatch, Bedrock, Rekognition, Route 53) | cents |
| **Running total** | **about $2 to 3 per day** |

[Insert the Cost Explorer spend-over-time graph and the Budget page; replace the estimates with the real figures.]

## 9. AI-DLC process evidence

The project followed the AI-Driven Development Lifecycle. For every phase the AI assistant (1) wrote an Inception document (goal, requirements, acceptance criteria, open questions)
in `docs/aidlc/`, (2) proposed the Terraform and code and showed the `terraform plan`, and the **human approved before anything was applied**, and (3) verified the result in Operations.
The evidence is in the commit history (`phase-N(inception|construction|operations): ...`), the per-phase documents and `AI-DLC-LOG.md`. Examples of the human review changing the outcome:

- The first apply of the NAT instance failed because `t4g.nano` is not available on the Free plan; the assistant stopped, the human chose `t4g.micro`.
- The SageMaker training job was refused because the new account's quota for `ml.m5.large` is 0; the assistant listed the available quotas and the human approved `ml.g5.xlarge` for a one-off job (about $0.02).
- The first app release failed its health checks because a Windows-made zip used backslash paths; the assistant diagnosed it from the instance's bootstrap log and a second plan was approved.
- DigitalPlat refused every free domain name, so the human chose to fall back to Route 53 Plan B.

[Rayyan Khan's contribution: describe here.] [Optional: screenshots of AI-DLC tool sessions.]

## 10. Limitations and honest notes

1. **Single NAT instance:** a single point of failure for outbound internet from the private subnets (cost decision).
2. **DNS (Plan B):** we could not obtain a free delegated domain (every DigitalPlat name was refused), so the Route 53 hosted zone `cloudscale-lf.example` is not delegated from a registrar
   and public resolvers cannot see it. Resolution is demonstrated by querying the zone's own name servers (`nslookup app.cloudscale-lf.example ns-...awsdns...`), which returns the CloudFront addresses.
   A custom hostname with an ACM certificate would need a registered domain.
3. **Synthetic training data:** the 98.75% hold-out accuracy is optimistic; real user text will score lower.
4. **Instance loss causes a short blip** (about 25 seconds in our test), not zero impact.
5. **Single-AZ database:** no failover; a deliberate cost decision.
6. **Minimal CSRF protection:** SameSite=Lax session cookie and JSON-only API endpoints.
7. **SNS email subscriptions need a one-time confirmation click** by each recipient; the app triggers the confirmation email at sign-in.

## 11. Teardown instructions

After grading, run `.\scripts\teardown.ps1` from the repository root. It asks you to type `destroy`, deletes the SageMaker endpoint, endpoint configs and models,
runs `terraform destroy` (buckets use `force_destroy`), deletes the SageMaker log groups and lists any billable resource that is left. Then delete the deployer user's access keys
yourself, keep the Budget until grading is finished, and take the cleanup screenshot (empty EC2, RDS, VPC and S3 consoles). [Insert cleanup screenshot after teardown.]
