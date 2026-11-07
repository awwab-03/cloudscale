# Phase 8 — CloudWatch dashboard, alarms and Route 53

## Inception

### Goal (plain language)
See how the system is doing at a glance (one dashboard), get an email when something is wrong (four alarms), and give the site a friendly DNS name (Route 53).

### Requirements
**Dashboard `CloudScale`** (widgets, all in us-east-1)
- ASG average CPU and number of InService instances (ASG group metrics enabled on the ASG).
- ALB `RequestCount`, `TargetResponseTime` (p50 and p90), `HealthyHostCount`, `HTTPCode_Target_5XX_Count`.
- Lambda `Invocations`, `Errors`, `Duration` for `cloudscale-thumbnailer`.
- SQS `ApproximateNumberOfMessagesVisible` for `image-jobs` and for `image-jobs-dlq`.

**Alarms → SNS `ops-alerts`** (alarm and OK notifications)
| Alarm | Condition |
|---|---|
| `cloudscale-asg-cpu-high` | ASG average CPU > 70% for 2 x 5 min |
| `cloudscale-alb-target-5xx` | `HTTPCode_Target_5XX_Count` sum > 5 in 5 min |
| `cloudscale-lambda-errors` | Lambda `Errors` >= 1 in 5 min |
| `cloudscale-dlq-not-empty` | DLQ visible messages >= 1 |

Missing data is treated as "not breaching" so idle periods don't alarm.

**Route 53** (DNS)
- Plan A: public hosted zone for a free domain/subdomain whose NS records are delegated to Route 53, ACM certificate (DNS-validated, us-east-1) on CloudFront, alias record `app.<domain>` to CloudFront.
- Plan B (if no working delegation by Sunday 12:00 PKT or signup is blocked): public hosted zone with a record pointing at the CloudFront domain; resolution demonstrated by querying the zone's own name servers; limitation explained in the report.
- The DNS part is planned after the provider decision; this first plan covers only the dashboard and alarms.

### Acceptance criteria
- `terraform plan` shows only the dashboard, four alarms and the ASG metrics setting; `validate` clean.
- After apply: dashboard visible with data on all widgets (those with traffic), alarms in `OK` or `INSUFFICIENT_DATA`, and each alarm's action is the `ops-alerts` topic.
- During the load test (later): the CPU alarm reaches `ALARM` and an email arrives at the alert address.

### Risks / notes
- **Cost:** CloudWatch dashboards cost $3/month each beyond the first 3 free dashboards; standard alarms are $0.10/month each beyond the first 10 free. Effectively $0 here. Route 53 hosted zone is $0.50/month.
- Enabling ASG group metrics adds no charge for the 1-minute group metrics.
- Alarms publish to `ops-alerts` through its default topic policy (same account).

### Open questions
- Plan A vs Plan B for DNS (provider research in progress).
