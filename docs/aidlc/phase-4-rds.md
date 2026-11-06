# Phase 4 — RDS PostgreSQL

## Inception

### Goal (plain language)
Create the relational database for users, items and claims. It must be private (no internet access), small and cheap, and its password must never appear in code or Git.

### Requirements
- RDS PostgreSQL 16 (16.15), `db.t4g.micro`, single-AZ, 20 GB gp3, encrypted at rest.
- DB subnet group using the two private-DB subnets; `publicly_accessible = false`; attached to `db-sg` only (5432 from `app-sg`).
- Master password managed by RDS in Secrets Manager (`manage_master_user_password = true`); no password in Terraform, state-visible variables or Git.
- Database `cloudscale`, master user `cloudscale_admin`.
- Backups retention 1 day (cost and Free-plan friendly); `skip_final_snapshot = true` and no deletion protection so teardown works.
- Tag `Project=CloudScale`. No IAM roles in this bolt (the EC2 role gets read on the secret ARN in the identity bolt).

### Acceptance criteria
- `terraform plan` shows only the DB subnet group and DB instance; `validate` clean.
- After apply: status `available`, `PubliclyAccessible=false`, `MultiAZ=false`, gp3 20 GB, in the private-DB subnets, only `db-sg` attached, master secret ARN present.

### Risks / notes
- **Hourly billed** (~$0.016/hr for db.t4g.micro, about $0.40/day, plus storage), within the CLAUDE.md plan.
- The Free plan may restrict RDS options. If the API rejects anything, I stop and report; nothing is worked around silently.
- Creation takes about 5–10 minutes.
- Secrets Manager secret costs about $0.40/month.
- Schema migration runs from the app on start (a later bolt), not here.

### Open questions
- None.
