# Phase 2 (+3b) — App, compute and CloudFront

## Inception

### Goal (plain language)
Get the Lost & Found website running on AWS, reachable over HTTPS: students sign up and sign in with Cognito, post lost/found items with a photo, browse and search, and claim items. The site must keep working if a server dies and must add servers when busy.

### Requirements
**App** (Python 3.12, Flask, gunicorn, Jinja, no SPA; boto3, psycopg v3)
- Sign up (email + code), sign in, sign out through Cognito (`SignUp`, `ConfirmSignUp`, `InitiateAuth` server-side); the ID token is verified against the pool's JWKS.
- Post lost/found item (title, notes, description, category, location, date, photo → S3 `originals/`), browse and search/filter, item detail, claim a found item (claim row + SNS publish + owner email subscription; these degrade gracefully until the SNS topic exists in a later bolt).
- `/health` (200 with a cheap DB ping), `/api/stress?ms=300` (CPU burn, only when SSM `/cloudscale/enable-stress` is `true`).
- Idempotent SQL migration (`users`, `items`, `claims`) runs on start, guarded by an advisory lock so several instances can start together.
- Secrets are read at runtime: DB credentials from the RDS Secrets Manager secret, Flask key from SSM. No secrets in the zip, user_data or Git.

**Compute**
- Launch template: AL2023 x86_64 `t3.micro`, `cloudscale-ec2-app` instance profile, no public IP, IMDSv2 required, SG `app-sg`.
- `user_data` installs Python 3.12, downloads `s3://<artifacts>/app/app-<version>.zip`, builds a venv, writes non-secret config, runs gunicorn (2 workers) as a systemd service on :8000.
- ASG: min 2 / desired 2 / max 4, private-app subnets, ELB health checks, target tracking at 50% average CPU, rolling instance refresh when the launch template changes (`app_version` variable).
- ALB (internet-facing, public subnets, `alb-sg`), target group on 8000 with `/health` check, listener on 80: default action 403, rule forwards only when header `X-Origin-Verify` matches a random value.

**CloudFront (3b)**
- Default behavior → ALB (HTTP origin, CachingDisabled, AllViewer origin request policy, sends `X-Origin-Verify`), HTTPS redirect.
- `/media/*` → S3 uploads bucket via OAC (cached; a CloudFront Function strips the `/media` prefix). Bucket policy gains a statement allowing only this distribution to read `originals/*` and `thumbnails/*`.

**Packaging**: `scripts/package_app.ps1` zips `app/` and uploads it to the artifacts bucket.

### Acceptance criteria
- `terraform plan` shows only compute/ALB/CloudFront/SSM/bucket-policy changes; `validate` clean.
- After apply: 2 InService instances, target group healthy, `https://<cloudfront>.cloudfront.net/health` returns 200, the ALB returns 403 when called directly without the header (and is unreachable except via CloudFront), sign up / sign in / post item with photo / claim work in the browser, photo loads via `/media/...`.
- First real proof of the NAT path (instances install packages) and of the DB connection.

### Risks / notes
- **Hourly cost added:** ALB ~$0.55/day, its 2 public IPv4 ~$0.24/day, 2× `t3.micro` ~$0.50/day (more when scaled to 4). Roughly **+$1.3–1.5/day**. CloudFront is free-tier-friendly.
- Free-plan restrictions may block ALB, CloudFront or instance types. If any API refuses, I stop and report.
- Email verification uses Cognito's built-in sender (about 50/day).
- Claim notifications need the SNS topic from a later bolt; until then the claim still saves and the SNS call is logged and skipped.
- Thumbnails and ML/AI buttons come in later bolts; for now the page shows the original photo.
- Minimal CSRF protection (SameSite=Lax session cookie only); acceptable for the coursework scope and noted in the report.

### Open questions
- None.

## Construction — approved plan
App (`app/`), `scripts/package_app.ps1`, and Terraform: launch template, ASG (2/2/4, CPU target 50%), ALB with `X-Origin-Verify` rule, target group `/health`, CloudFront (ALB default, `/media/*` to S3 via OAC + strip-prefix function), SSM `/cloudscale/enable-stress`, uploads bucket policy statement for the distribution. Plan 1: 12 to add, 1 to change, 0 to destroy.
Approved by Awwab Aamir, 2026-11-07 (upload app 1.0.0 and apply).

Incidents and fixes (human-approved):
1. **ASG creation error** "Access denied when attempting to assume role AWSServiceRoleForAutoScaling": AWS was still creating its service-linked role; the retry succeeded (ASG had 2 instances). Terraform tainted the ASG only because the apply errored; `terraform untaint` (state only), then applied the remaining scaling policy (1 to add).
2. **Targets unhealthy**: `Compress-Archive` wrote backslash separators; Linux `unzip` exited 1 and `set -e` stopped the bootstrap. Fix: package with Python `zipfile`, tolerate unzip warning exit code 1 in `user_data`, bump `app_version` to 1.0.1. Plan 2: 0 to add, 2 to change, 0 to destroy (launch template + ASG → rolling instance refresh). Approved by Awwab Aamir, 2026-11-07 (upload app 1.0.1 and apply).

## Operations
- **Built:** ALB `cloudscale-alb`, target group, ASG `cloudscale-asg` (2 x t3.micro in 1a/1b private-app), CloudFront distribution, CloudFront function, OAC.
- **Decisions:** ALB is HTTP-only behind CloudFront (no custom domain cert yet); secret header shared via Terraform state only; stress endpoint off by default; app reads secrets at runtime.
- **Verification:**
  - Target group: 2 healthy; instance refresh Successful (100%); instances InService/Healthy in us-east-1a and us-east-1b.
  - `https://<cloudfront>/health` returns 200 `{"status":"ok","version":"1.0.1"}`, which proves the NAT path (package install), S3 endpoint download, Secrets Manager read and the DB connection plus migration.
  - `/` and `/login` return 200; HTTP redirects 301 to HTTPS; `/api/stress` returns 404 with the flag off; `/media/<missing>` returns 403 (S3 via OAC, key absent).
  - ALB DNS called directly from the internet gets no response (security group allows only the CloudFront prefix list), so the ALB cannot be reached except through CloudFront.
- **Not yet verified:** browser flow (sign up with a real email code, sign in, post an item with photo, photo loads via `/media/...`, claim); to be done by Awwab and recorded.
- **Screenshots to take** (blur account ID): `phase-2-site-home.png`, `phase-2-signup-confirm.png`, `phase-2-post-item.png`, `phase-2-item-with-photo.png`, `phase-2-alb-target-group-healthy.png`, `phase-2-asg-instances.png`, `phase-2-cloudfront-distribution.png`, `phase-2-ec2-instances-private.png` (no public IPs).

## Release 1.3.0 (handover flow), 2026-11-07
- **Why:** during Awwab's browser test the question "how do the two users arrange the handover after a claim?" exposed a gap: the owner's claim email had no contact details, nobody could set `returned`, and claim messages were publicly visible.
- **Change:** the claim email now includes the claimant's email address (private email only); the owner gets a "Mark as returned" action (`POST /items/<id>/return`, owner only, only for `claimed` items); claim messages are visible only to the owner and the claimant (others see a count); the claim form tells the claimant to leave a way to be reached.
- **Plan:** 0 to add, 2 to change, 0 to destroy (launch template and ASG, rolling instance refresh). Approved by Awwab Aamir, 2026-11-07 (upload app 1.3.0 and apply).
- **Verification:** refresh Successful (100%), 2 healthy targets, `/health` reports 1.3.0, item page returns 200. Route behaviour tested locally with a mocked database: a stranger cannot read claim messages and gets 403 on return; the owner can return a claimed item once; the button disappears afterwards; the notification text includes the reply address.
