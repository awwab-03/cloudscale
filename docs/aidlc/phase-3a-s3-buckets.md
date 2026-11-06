# Phase 3a — S3 buckets

## Inception

### Goal (plain language)
Create the two storage buckets the app needs: one for user photos (uploads) and one for the app's deployable zip and ML files (artifacts). Both are private, versioned and encrypted. Photos move to cheaper storage as they age.

### Requirements
- `cloudscale-uploads-<account-id>`: prefixes `originals/`, `thumbnails/`, `meta/` (created by the app and Lambda; S3 has no real folders). Block Public Access ON, versioning ON, SSE-S3 encryption, `force_destroy = true`.
- Uploads lifecycle: `originals/` → STANDARD_IA at 30 days → GLACIER_IR at 90 days; noncurrent versions expire after 30 days; abort incomplete multipart uploads after 1 day.
- `cloudscale-artifacts-<account-id>`: prefixes `app/` and `ml/`. Block Public Access ON, versioning ON, SSE-S3, `force_destroy = true`, noncurrent versions expire after 30 days.
- Bucket policies: deny any request not using HTTPS. (CloudFront OAC read access to `/media/*` is added in the CloudFront bolt, and the S3 → SQS event in the messaging bolt, so each is reviewed with the resource it belongs to.)
- Tag `Project=CloudScale`. No IAM roles in this bolt.

### Why (for the report)
- Uploads must not live on EC2 disks because ASG instances are disposable.
- Lifecycle: photos are rarely viewed after an item is resolved. Versioning protects against accidental overwrite or delete.
- A separate artifacts bucket keeps deployable code and model files out of the user-content bucket and lets IAM scope each role to the right prefix.

### Acceptance criteria
- `terraform plan` shows only S3 resources; `validate` clean.
- After approved apply: both buckets exist; Block Public Access fully on; versioning Enabled; lifecycle rules match above; HTTPS-only policy present; no public ACL/policy.

### Notes / limits
- S3 does not transition objects smaller than 128 KB to STANDARD_IA/Glacier IR, so small thumbnails are unaffected and small originals may stay in STANDARD. Documented honestly in the report.
- Cost: negligible at this scale (cents). Nothing hourly.

### Open questions
- None.
