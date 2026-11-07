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
