# AI-DLC Log

Each phase is a bolt: Inception → Construction → Operations.

## Bolt 0 — Repo bootstrap — 2026-11-07 PKT
- Inception: goal/requirements/acceptance for repo + safety rails → docs/aidlc/phase-0-bootstrap.md
- Construction: AI proposed gitignore/gitattributes/skeletons and a private `gh` repo; human review: Awwab approved the plan unchanged
- Operations: repo pushed to github.com/awwab-03/cloudscale (private); verified with `gh repo view` and a secret scan
- Evidence screenshots: phase-0-github-repo.png

## Bolt 1 — Networking — 2026-11-07 PKT
- Inception: VPC/subnets/NAT instance/SG requirements and acceptance criteria → docs/aidlc/phase-1-networking.md
- Construction: AI proposed t4g.nano NAT instance; human review: apply hit a Free-plan block, Awwab approved t4g.micro instead (no plan upgrade)
- Operations: applied in two steps (38 + 4 resources); verified via AWS CLI (NAT running, source/dest check off, SSM online, routes and SG rules correct)
- Evidence screenshots: phase-1-vpc-resource-map.png, phase-1-route-tables.png, phase-1-security-groups.png, phase-1-nat-instance.png
