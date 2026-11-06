# Phase 0 — Repo bootstrap

## Inception

### Goal (plain language)
Set up the project repository so that all later work (infrastructure, app, ML, docs) lives in one private GitHub repo, with safety rails that prevent committing secrets and with the AI-DLC paper trail ready.

### Requirements
- Local git repo, private GitHub repo `cloudscale`, history pushed.
- `.gitignore` covers `*.tfstate*`, `.terraform/`, `*.tfvars` (keep `*.tfvars.example`), `.env*`, `*.pem`, `build/`, `dist/`, `*.zip`, `__pycache__/`, `.venv/`.
- `.gitattributes` forces LF for `*.sh` and `*.tpl`.
- README skeleton, `AI-DLC-LOG.md`, `docs/` folders, `docs/iam-justification.md` stub.
- At least 3 incremental commits, scanned for secrets before each.
- No AWS changes.

### Acceptance criteria
- `gh repo view cloudscale` shows a PRIVATE repo with the commits.
- `git ls-files` contains no state files, keys, or tfvars.
- Secret scan (`AKIA`, `aws_secret_access_key`, `password=`) finds nothing.

### Open questions
- Instructor/TA GitHub username for the collaborator invite (ask Awwab).

## Construction — approved plan
Create git repo, `.gitignore`, `.gitattributes`, README/log/IAM-doc skeletons; push to private repo `cloudscale`.
Approved by Awwab Aamir, 2026-11-07 (plan approved in session).

## Operations
- **Built:** private repo https://github.com/awwab-03/cloudscale, 3+ incremental commits on `main`. `docs/spec/` (assignment PDF, deployer IAM policy) also committed; contains no secrets.
- **Decisions:** `.tfvars` ignored except `*.tfvars.example`; `.terraform.lock.hcl` will be committed.
- **Verification:** `gh repo view` reports PRIVATE; secret scan (`AKIA`, `aws_secret_access_key`, `password=`) clean on all non-brief files (the brief itself only quotes the rule text).
- **Screenshots to take:** `docs/screenshots/phase-0-github-repo.png` (private repo page showing commits). No AWS account IDs or keys visible.
- **Pending:** instructor GitHub username for collaborator invite.
