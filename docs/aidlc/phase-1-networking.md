# Phase 1 — Networking

## Inception

### Goal (plain language)
Build the private network the whole app will live in: a VPC with public, private-app and private-DB subnets in two AZs; internet access for private instances through one cheap NAT instance; and security groups that only allow the traffic we need (no SSH anywhere).

### Requirements
- VPC 10.20.0.0/16, AZs us-east-1a/b; public 10.20.1/2.0/24, private-app 10.20.11/12.0/24, private-DB 10.20.21/22.0/24.
- IGW for public subnets. One NAT instance (t4g.nano, AL2023 + iptables masquerade) in public subnet A, source/dest check off, Elastic IP; private-app route tables send 0.0.0.0/0 to its ENI. DB subnets have no internet route.
- Free S3 gateway endpoint on the private route tables.
- Security groups: `alb-sg` (80 from CloudFront origin-facing prefix list), `app-sg` (8000 from alb-sg), `db-sg` (5432 from app-sg), `nat-sg` (all from private-app CIDRs).
- NAT instance reachable only via SSM Session Manager (role with `AmazonSSMManagedInstanceCore`).
- Everything tagged `Project=CloudScale`; no NAT Gateway.

### Acceptance criteria
- `terraform plan` shows only the resources above; `validate` and `fmt` clean.
- After approved apply: NAT instance running, source/dest check false; private route tables target NAT ENI; DB route table has no default route; SGs match the rules above; no `0.0.0.0/0` inbound rule anywhere.
- (With approval) a temporary private instance reaches the internet via the NAT's Elastic IP.

### Known trade-offs
- Single NAT instance is a single point of failure (documented in the report).
- Hourly-billed: NAT t4g.nano (~$0.12/day) + its Elastic IP (~$0.12/day).

### Open questions
- None blocking. Test instance for the NAT check needs Awwab's OK before launching.

## Construction — approved plan
Terraform in `infra/`: VPC 10.20.0.0/16, 6 subnets over 2 AZs, IGW, route tables, S3 gateway endpoint, 4 security groups, NAT instance + EIP + SSM-only IAM role.
Plan 1: 39 to add. Apply created 38; the NAT instance was rejected (`t4g.nano` not Free-plan eligible). Stopped and reported per CLAUDE.md §2.6.
Human decision: use `t4g.micro` (Free-plan eligible, ~$0.20/day from credit); no plan upgrade needed. Plan 2: 4 to add (NAT, EIP, 2 routes).
Approved by Awwab Aamir, 2026-11-07 (both applies approved in chat).

## Operations
- **Built:** VPC and subnets, IGW, NAT instance (`t4g.micro`, source/dest check off, EIP), S3 gateway endpoint, alb/app/db/nat security groups.
- **Decisions:** AL2023 + iptables NAT (no marketplace AMI); NAT size raised nano→micro due to Free-plan restriction; single NAT is a known single point of failure.
- **Verification (CLI):** NAT `running`, SourceDestCheck=False, SSM PingStatus Online; both private-app route tables send 0.0.0.0/0 to the NAT ENI; DB route table has no default route; public route table → IGW; zero inbound 0.0.0.0/0 rules on alb/app/db SGs.
- **Not yet verified:** actual outbound internet from a private instance (needs a temporary instance, pending approval; will happen naturally when the ASG launches in Bolt 2).
- **Screenshots to take** (`docs/screenshots/`, blur account ID, never show keys): `phase-1-vpc-resource-map.png`, `phase-1-route-tables.png`, `phase-1-security-groups.png`, `phase-1-nat-instance.png`.
