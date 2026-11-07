# Phases 5 + 6 — Async image processing and notifications

## Inception

### Goal (plain language)
When someone uploads a photo, the website should answer immediately and a background worker should shrink the photo, tag it ("wallet", "keys") and hide inappropriate pictures. When someone claims an item, its owner should get an email. Operators get alerts through a separate channel.

### Requirements
**Async pipeline (Phase 5)**
- S3 `ObjectCreated` events for prefix `originals/` → SQS `image-jobs` (SSE, visibility timeout 360 s) with a DLQ `image-jobs-dlq` (`maxReceiveCount = 3`, 14-day retention).
- Lambda `cloudscale-thumbnailer` (Python 3.12, 512 MB, 60 s, **not in the VPC**), SQS event source (batch 5, partial-batch failures):
  1. download the original, resize to max 640 px JPEG → `thumbnails/<name>.jpg`
  2. Rekognition `DetectModerationLabels` (confidence ≥ 60); if flagged: no thumbnail, write `meta/<name>.json` with `flagged: true`
  3. Rekognition `DetectLabels` (max 8, confidence ≥ 70) → `meta/<name>.json` with the labels
- Pillow is packaged for Linux from Windows: `pip install --platform manylinux... --only-binary=:all: --python-version 3.12 --target build/thumbnailer pillow` (`scripts/build_lambda.ps1`); Terraform `archive_file` zips it.
- Role `cloudscale-lambda-thumbnailer`: SQS receive/delete/attributes on `image-jobs`; S3 `GetObject` on `originals/*`, `PutObject` on `thumbnails/*` and `meta/*`; Rekognition `DetectLabels` and `DetectModerationLabels` (`Resource "*"`, no resource-level support, documented); logs on its own log group only.
- Because the Lambda is outside the VPC it cannot reach RDS, so results go to `meta/*.json`. The app reads the meta file on the item page (labels, flagged, processing) and copies the labels into `items.labels`.
- **Privacy tightening:** CloudFront now serves only `thumbnails/*` (not `originals/*`). Flagged photos never get a thumbnail, so they are never displayed. The app release (1.2.0) shows thumbnails and hides images that failed moderation.

**Notifications (Phase 6)**
- SNS topic `claim-notifications` (the app already publishes with attribute `owner_email` and subscribes each user's email with a filter policy on sign-in).
- SNS topic `ops-alerts` with an email subscription to `i220971@nu.edu.pk` (needs a one-time confirmation click; used by CloudWatch alarms in the monitoring bolt).

### Acceptance criteria
- `terraform plan` shows only SQS, SNS, Lambda, IAM, log group, S3 notification and the bucket-policy tightening.
- Upload a photo in the site: within seconds `thumbnails/<name>.jpg` and `meta/<name>.json` exist, the item page shows labels; an invalid message ends up in the DLQ after 3 tries.
- A claim publishes to SNS; a subscribed (confirmed) owner receives the email.
- Policy inspection: no wildcard actions; only the Rekognition statement uses `*`.

### Risks / notes
- **Free plan:** Rekognition and Lambda are checked with a tiny test call before building; if blocked, I stop and report.
- **Cost:** Lambda, SQS and SNS are effectively free at this volume; Rekognition about $0.001 per image per call (two calls per photo); no hourly charges added.
- SNS email subscriptions must be confirmed by the recipient. Each owner confirms once (the app triggers the confirmation email at their sign-in), and the first claim emails will only reach confirmed subscribers.
- Removing `originals/*` from the CloudFront policy means any photo uploaded before this change would stop displaying if it has no thumbnail. Only demo data exists so far (no photos).

### Open questions
- None.

## Construction — approved plan
Terraform: SQS `image-jobs` + DLQ (`maxReceiveCount` 3), queue policy for S3, S3 notification on `originals/`, Lambda `cloudscale-thumbnailer` + role + log group + event source mapping, SNS `claim-notifications` and `ops-alerts` (+ email subscription), bucket policy tightened to `thumbnails/*`. App 1.2.0 (thumbnails, labels, moderation state). Plan: 12 to add, 3 to change, 0 to destroy.
Approved by Awwab Aamir, 2026-11-07 (upload app 1.2.0 and apply).

## Operations
- **Built:** queues, Lambda (python3.12, 512 MB, 60 s, no VPC), event source mapping (batch 5, partial failures), two SNS topics, app 1.2.0 via rolling refresh (Successful, 100%).
- **Decisions:** Lambda writes `meta/*.json` (cannot reach RDS); app persists labels to `items.labels` on first item view; CloudFront serves thumbnails only, so originals, meta and flagged photos are never public; flagged photos get no thumbnail.
- **Verification:**
  - Uploaded a generated 1600x1200 JPEG to `originals/`: `thumbnails/*.jpg` (6.8 KB, image/jpeg) and `meta/*.json` (`flagged: false`, labels from Rekognition) appeared in about 5 s; queue and DLQ empty afterwards.
  - Via CloudFront: thumbnail returns 200 `image/jpeg`; the original and the meta file return 403.
  - Lambda role inspected: no wildcard actions; only the Rekognition statement uses `Resource "*"`. Lambda has no VpcConfig. Redrive policy: DLQ with `maxReceiveCount` 3. `/health` through CloudFront reports 1.2.0.
  - Test objects deleted afterwards (versioning leaves delete markers that expire after 30 days).
- **Not yet verified:** DLQ path with a real poison message (takes about 3 visibility timeouts); claim email end to end (needs a confirmed email subscription and a claim from a second account); the moderation branch with a real flagged image (only tested with stubs).
- **Screenshots to take** (blur account ID): `phase-5-sqs-queues.png` (image-jobs with DLQ redrive), `phase-5-s3-event-notification.png` (uploads bucket → Properties → Event notifications), `phase-5-lambda-config.png`, `phase-5-lambda-trigger-sqs.png`, `phase-5-s3-thumbnails-meta.png` (bucket prefixes after a real upload), `phase-5-item-with-labels.png` (item page with Rekognition tags), `phase-6-sns-topics.png`, `phase-6-claim-email.png` (the owner's email), `phase-6-ops-alerts-subscription.png`.
