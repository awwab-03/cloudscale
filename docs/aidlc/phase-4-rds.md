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

## Construction — approved plan
`infra/database.tf`: DB subnet group (private-DB subnets) + `db.t4g.micro` PostgreSQL 16.15, single-AZ, 20 GB gp3 encrypted, private, `manage_master_user_password = true`. Plan: 2 to add, 0 to change, 0 to destroy.
Approved by Awwab Aamir, 2026-11-07.

## Operations
- **Built:** `cloudscale-db` (RDS PostgreSQL 16.15), subnet group `cloudscale-db-subnets`.
- **Decisions:** password in RDS-managed Secrets Manager secret (ARN is a Terraform output, value never read); 1-day backups, no final snapshot, no deletion protection for easy teardown; no Free-plan block encountered.
- **Verification (CLI):** status `available`; PubliclyAccessible=False; MultiAZ=False; gp3 20 GB; StorageEncrypted=True; in the CloudScale VPC; only `cloudscale-db-sg` attached; master secret status `active`.
- **Not yet verified:** an actual connection from an app instance (happens in the app bolt, when the EC2 role can read the secret).
- **Screenshots to take** (blur account ID, never reveal the password): `phase-4-rds-config.png` (Configuration tab: class, storage, Multi-AZ no), `phase-4-rds-connectivity.png` (Connectivity & security: Publicly accessible = No, security group, subnet group), `phase-4-secret.png` (Secrets Manager list showing the `rds!db-...` secret; do NOT click Retrieve secret value).
