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
