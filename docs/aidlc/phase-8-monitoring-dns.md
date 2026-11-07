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

## Construction — approved plan (dashboard and alarms)
`infra/monitoring.tf`: dashboard `CloudScale` (8 widgets), alarms `cloudscale-asg-cpu-high`, `cloudscale-alb-target-5xx`, `cloudscale-lambda-errors`, `cloudscale-dlq-not-empty` (all alarm and OK actions to `ops-alerts`), plus ASG group metrics (`GroupInServiceInstances`, `GroupDesiredCapacity`, `GroupTotalInstances`, 1-minute) in `infra/compute.tf`. Plan: 5 to add, 1 to change, 0 to destroy.
Approved by Awwab Aamir, 2026-11-07.

## Operations (dashboard and alarms)
- **Built:** the dashboard and four alarms; ASG metrics enabled in place (no instance refresh).
- **Decisions:** `treat_missing_data = notBreaching` so idle periods stay in OK; alarms notify both on ALARM and on OK; alarm thresholds exactly as in the brief.
- **Verification (CLI):** `apply` created 5 and changed 1; `describe-alarms` lists the four alarms, each with the `ops-alerts` topic as its action (state `INSUFFICIENT_DATA` right after creation, which is normal until the first datapoints); `get-dashboard` returns 8 widgets; ASG reports the three enabled metrics.
- **To prove during the load test:** CPU alarm reaches `ALARM` and the email arrives at `i220971@nu.edu.pk`; dashboard shows InService instances rising to 3-4.
- **DNS (Route 53):** pending provider decision. Provider research: DigitalPlat FreeDomain documents delegating a registered domain to external nameservers, but which extensions are free and how fast approval is could not be verified from the public docs; fallback is Plan B (hosted zone queried through its own name servers).
- **Screenshots to take** (blur account ID): `phase-8-dashboard.png` (CloudWatch → Dashboards → CloudScale, populated after some traffic), `phase-8-alarms-list.png`, `phase-8-alarm-asg-cpu-config.png` (threshold 70, 2 x 5 min, action ops-alerts), later `phase-8-alarm-fired.png` and `phase-8-alarm-email.png` from the load test.

## Load test and scale-out (run 2026-11-07, approved by Awwab Aamir)
- **Method:** set SSM `/cloudscale/enable-stress` to `true` (version 2), ran `scripts/load_test.py --concurrency 40 --duration 840 --ms 300` against the CloudFront URL, then set the flag back to `false` (version 3); probe afterwards returned 404 again.
- **Results:** 14,819 requests, **0 errors**, average 17.6 req/s. With 2 instances: about 13 req/s, p50 about 3.0 s, p90 about 3.4 s, group CPU about 98%. After the ASG scaled out to **4 instances** (target tracking policy `cloudscale-cpu-target-50` triggered by its high alarm; desired capacity 2 → 4): about 26 req/s, p50 about 1.5 s, p90 about 2.1 s, zero errors.
- **Alarm:** `cloudscale-asg-cpu-high` changed OK → ALARM at 21:11:56 PKT (two 5-minute periods above 70%) and notifies `ops-alerts`.
- **Note for the report:** requests were deliberately CPU-heavy (300 ms of busy work each), so absolute latency is high; the point is that throughput doubled and latency halved when capacity doubled, with no failed requests. Scale-in back to 2 happens after the target-tracking cooldown.
- **Screenshots to take:** `phase-8-dashboard-load.png` (CPU climbing, InService rising to 4), `phase-8-alarm-fired.png` (alarm in ALARM), `phase-8-alarm-email.png` (email from AWS to the alert address), `phase-8-asg-activity.png` (ASG → Activity: launches triggered by the alarm), `phase-8-asg-4-instances.png` (EC2 list with 4 running instances).
