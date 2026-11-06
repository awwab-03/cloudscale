# IAM justification

Every role is least-privilege and named `cloudscale-*`. No `AdministratorAccess`.
`"Resource": "*"` appears only where the API has no resource-level permissions; each such case is listed here.

| Role / policy | Permissions | Why | Wildcard resource? |
|---|---|---|---|
_Rows added per phase._
| `cloudscale-nat-instance` (Bolt 1) | AWS-managed `AmazonSSMManagedInstanceCore` | Lets the NAT instance be managed via Session Manager so no SSH/port 22 is needed | No (managed policy; no custom wildcards) |
