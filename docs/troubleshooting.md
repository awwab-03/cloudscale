# Troubleshooting

Problems we hit while building and operating CloudScale, with the quick check for each. Longer
write-ups are in `docs/aidlc/`.

| Symptom | Likely cause | What to check |
|---|---|---|
| Site returns 502/503 right after `terraform apply` | Instances still bootstrapping from the artifacts bucket | ALB target group health; confirm the zip for `var.app_version` exists in the artifacts bucket (run `scripts/package_app.ps1` first) |
| New instances never become healthy | App zip missing or wrong version | `/var/log/cloud-init-output.log` on the instance (Session Manager) |
| `terraform apply` fails creating the ASG | Service-linked role not ready yet | Re-run apply after a minute |
| Instance type rejected | Free-plan account restricts instance types | Use `t3.micro` as configured in `infra/compute.tf` |
| SageMaker training job fails with a quota error | New accounts have quota 0 for `ml.m5.large` | Launch with `python ml\launch_training.py ml.g5.xlarge` |
| Lambda thumbnailer import error | Pillow wheel built for the wrong OS | Rebuild with `scripts/build_lambda.ps1` (builds Linux wheels) |
| Lambda zip fails to load | Windows path separators inside the zip | Rebuild with `scripts/build_lambda.ps1` |
| No alarm emails | `ops-alerts` subscription not confirmed | Click the confirmation link AWS emailed to the alert address |
| `/stress` returns 404 | `enable-stress` flag is false or cached | Set the SSM parameter to `true` and wait about 30 seconds |
| Seed script cannot reach the database | RDS is in private subnets | Run `seed_db.py` on an app instance through Session Manager (see README) |

## Useful commands

```powershell
# Which instances are in the Auto Scaling group?
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names cloudscale-asg --query "AutoScalingGroups[0].Instances[].[InstanceId,LifecycleState,HealthStatus]" --output table

# Recent scaling activity
aws autoscaling describe-scaling-activities --auto-scaling-group-name cloudscale-asg --max-items 5
```
