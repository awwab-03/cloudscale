# IAM justification

Every role is least-privilege and named `cloudscale-*`. No `AdministratorAccess`.
`"Resource": "*"` appears only where the API has no resource-level permissions; each such case is listed here.

| Role / policy | Permissions | Why | Wildcard resource? |
|---|---|---|---|
_Rows added per phase._
