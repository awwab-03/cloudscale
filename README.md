# CloudScale — Campus Lost & Found on AWS

CS-4075 Cloud Computing semester project, FAST-NUCES Islamabad.
Team: Awwab Aamir (22i-0971), Rayyan Khan (22i-1002).

A Flask app where students post lost/found items, search, and claim items,
running on AWS (VPC, EC2 ASG + ALB, CloudFront, RDS, S3, SQS/Lambda, SNS,
Cognito, SageMaker, Bedrock, CloudWatch, Route 53). Region: us-east-1.

See `CLAUDE.md` for the full brief and `AI-DLC-LOG.md` for the build log.

## Status
| Bolt | Phase | Status |
|---|---|---|
| 0 | Repo bootstrap | done |
| 1 | Networking | done |
| 3a | S3 buckets | done |
| 4 | RDS PostgreSQL | done |
| 7 | Cognito + IAM | done |
| 2 | App, ASG, ALB, CloudFront | deployed (browser test pending) |
| 10 | SageMaker + Bedrock | deployed |
| 5+6 | SQS, Lambda thumbnailer, SNS | deployed (app 1.2.0) |

## Setup / Deploy / Teardown
_To be filled in as phases complete._

## Safety
No secrets are committed. `*.tfstate*`, `*.tfvars`, `.env*`, and `*.pem` are gitignored.
