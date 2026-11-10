# CloudScale: Campus Lost & Found on AWS

**Course:** CS-4075 Cloud Computing, FAST-NUCES Islamabad. **Instructor:** Dr. Basharat Hussain.
**Team:** Awwab Aamir (22i-0971), Rayyan Khan (22i-1002). **Region:** us-east-1.
**Repository (private, TA/evaluator added as collaborator):** <https://github.com/awwab-03/cloudscale>  *(collaborator: `Abdul-Moeez4`, invitation accepted)*

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

**Fig. 1. VPC resource map:** `cloudscale-vpc` with public, private-app and private-DB subnets in us-east-1a and us-east-1b and their route tables.

![Fig. 1 VPC resource map](../screenshots/phase-1-vpc-resource-map.png)

**Fig. 2. Security group `cloudscale-alb-sg`:** the only inbound rule is HTTP 80 from the CloudFront managed prefix list.

![Fig. 2 ALB security group inbound rule](../screenshots/phase-1-alb-sg-inbound.png)

**Fig. 3. Uploads bucket lifecycle rules:** tiering for `originals/`, expiry of noncurrent versions and abort of incomplete multipart uploads. The account number in the bucket name is part of the bucket's real name.

![Fig. 3 S3 lifecycle rules](../screenshots/phase-3a-uploads-lifecycle.png)

**Fig. 4. RDS PostgreSQL `cloudscale-db`:** `db.t4g.micro`, single AZ, available, with the master credentials held in Secrets Manager and no internet access gateway.

![Fig. 4 RDS instance](../screenshots/phase-4-rds-connectivity.png)

**Fig. 5. Identity:** the Cognito user pool, and the `cloudscale-ec2-app` role (one AWS-managed policy for Session Manager plus one scoped inline policy).

![Fig. 5a Cognito user pool](../screenshots/phase-7-cognito-pool.png)

![Fig. 5b EC2 app role](../screenshots/phase-7-iam-policy-json.png)

**Fig. 6. The site, the load balancer, the Auto Scaling group and CloudFront.** The home page over HTTPS; two healthy targets in the target group; the ASG with limits 2 to 4 and the launch template; the CloudFront behaviours (default to the ALB, `/media/*` to S3).

![Fig. 6a Site home page](../screenshots/phase-2-site-home.png)

![Fig. 6b Target group, 2 healthy](../screenshots/phase-2-alb-target-group-healthy.png)

![Fig. 6c Auto Scaling group](../screenshots/phase-2-asg-config.png)

![Fig. 6d CloudFront behaviours](../screenshots/phase-2-cloudfront-behaviors.png)

**Fig. 7. Asynchronous image pipeline:** the thumbnailer Lambda with its SQS trigger, and an item page whose thumbnail and Rekognition tags (Electronics, Phone, Mobile Phone) were produced by it.

![Fig. 7a Lambda thumbnailer](../screenshots/phase-5-lambda-config.png)

![Fig. 7b Item with image tags](../screenshots/phase-5-item-with-labels.png)

**Fig. 8. Claim notification:** the email the owner received through SNS after another user claimed the item. It carries the claimant's name, message and contact address.

![Fig. 8 Claim email](../screenshots/phase-6-claim-email.png)

**Fig. 9. SageMaker serverless endpoint `cloudscale-category`:** status InService, type Serverless.

![Fig. 9 SageMaker endpoint](../screenshots/phase-10-endpoint-serverless.png)

**Fig. 10. AI helpers in the post form:** "Suggest category" (our SageMaker model) and "Write description with AI" (Bedrock Nova Micro).

![Fig. 10 Post form with AI helpers](../screenshots/phase-10-form-ai.png)

**Fig. 11. Route 53 (Plan B):** querying the hosted zone's own name server returns the CloudFront addresses for `app.cloudscale-lf.example`.

![Fig. 11 nslookup against the Route 53 name server](../screenshots/phase-8-nslookup.png)

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
**Fig. 12. CloudWatch dashboard `CloudScale` during the load test:** CPU rising above the 70% alarm line, instance count going from 2 to 4, request count and response time.

![Fig. 12 Dashboard under load](../screenshots/phase-8-dashboard-load.png)

**Fig. 13. The `cloudscale-asg-cpu-high` alarm in ALARM state:**

![Fig. 13 Alarm fired](../screenshots/phase-8-alarm-fired.png)

**Fig. 14. The alarm email delivered through the `ops-alerts` SNS topic:**

![Fig. 14 Alarm email](../screenshots/phase-8-alarm-email.png)

**Fig. 15. Auto Scaling activity history:** scale-out from 2 to 4 instances by the target-tracking policy, and scale-in back to 2 afterwards.

![Fig. 15 ASG activity](../screenshots/phase-8-asg-activity.png)

**Fig. 16. EC2 instances after the test:** the NAT instance and the app instances, with the scaled-in ones terminated.

![Fig. 16 EC2 instances](../screenshots/phase-8-asg-4-instances.png)

## 6. Failure demonstration

With two healthy instances (one per AZ) we terminated the us-east-1a instance while probing the site once a second (258 probes over 9 minutes).
**254 requests returned 200.** The four failures (two 502s and two 5-second timeouts) all happened within about 25 seconds of the termination,
before the ALB stopped sending traffic to the dead target. After that the site was served by the remaining instance without errors. The Auto Scaling group
launched a replacement in us-east-1a and the target group was back to two healthy targets about four minutes after the termination, with no manual action.
So an instance loss is visible as a short blip but not as an outage. This scenario is also shown live in the demo video.

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

**Fig. 17. The AWS Budget "Cloud Scale"** ($100 monthly cost budget with alert thresholds). AWS billing data lags by about a day, so the Budget page showed $0.00 spent when this screenshot was taken.

![Fig. 17 AWS Budget](../screenshots/budget-cloud-scale.png)

**Fig. 18. Cost Explorer, daily cost grouped by service, 7 to 8 November 2026** (usage charges before the $100 credit is applied). Measured spend was **$4.49 in total, an average of $2.24 per day, across 20 services**, with EC2 instances, Elastic Load Balancing, RDS, VPC (public IPv4 addresses), Route 53, Secrets Manager, SageMaker and Rekognition as the main items. This matches the estimate in the table above (about $2 to 3 per day). AWS marks the most recent days as provisional (the asterisks on the dates), so the final figures may be slightly higher. At this rate the $100 credit is far from exhausted. The per-item figures in the table are estimates from published prices; the totals in this paragraph are measured.

![Fig. 18 Cost Explorer daily cost by service](../screenshots/cost-explorer.png)

**Fig. 19. Budget alert recipients verified.** Both alert recipients (`awwabcms@gmail.com` and `i220971@nu.edu.pk`) show as Verified, so the 50% and 80% actual-cost alerts and the 100% forecasted-cost alert can be delivered. The budget health status is Healthy.

![Fig. 19 Budget email verification](../screenshots/budget-alerts-verified.png)

## 9. AI-DLC process evidence

The project followed the AI-Driven Development Lifecycle. For every phase the AI assistant (1) wrote an Inception document (goal, requirements, acceptance criteria, open questions)
in `docs/aidlc/`, (2) proposed the Terraform and code and showed the `terraform plan`, and the **human approved before anything was applied**, and (3) verified the result in Operations.
The evidence is in the commit history (`phase-N(inception|construction|operations): ...`), the per-phase documents and `AI-DLC-LOG.md`. Examples of the human review changing the outcome:

- The first apply of the NAT instance failed because `t4g.nano` is not available on the Free plan; the assistant stopped, the human chose `t4g.micro`.
- The SageMaker training job was refused because the new account's quota for `ml.m5.large` is 0; the assistant listed the available quotas and the human approved `ml.g5.xlarge` for a one-off job (about $0.02).
- The first app release failed its health checks because a Windows-made zip used backslash paths; the assistant diagnosed it from the instance's bootstrap log and a second plan was approved.
- DigitalPlat refused every free domain name, so the human chose to fall back to Route 53 Plan B.

### Team contribution

The work was split roughly 60% Awwab Aamir and 40% Rayyan Khan.

- **Awwab Aamir (22i-0971), about 60%:** hands-on deployment and operation of the AWS environment: running the AI-assisted workflow, reviewing and approving each `terraform plan`, applying it, verifying each phase, and capturing the evidence.
- **Rayyan Khan (22i-1002), about 40%:** most of the application testing, the proofreading of the report and documentation, the budgeting and cost tracking, and the load testing (running `scripts/load_test.py` against the CloudFront URL and observing the Auto Scaling scale-out).

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
yourself, keep the Budget until grading is finished, and take the cleanup screenshot (empty EC2, RDS, VPC and S3 consoles). The cleanup screenshot is submitted after teardown, as the assignment requires.
