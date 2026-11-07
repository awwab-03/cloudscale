# IAM justification

Every role is least-privilege and named `cloudscale-*`. No `AdministratorAccess`.
`"Resource": "*"` appears only where the API has no resource-level permissions; each such case is listed here.

| Role / policy | Permissions | Why | Wildcard resource? |
|---|---|---|---|
| `cloudscale-nat-instance` (Bolt 1) | AWS-managed `AmazonSSMManagedInstanceCore` | Lets the NAT instance be managed via Session Manager so no SSH/port 22 is needed | No (managed policy; no custom wildcards) |
| `cloudscale-ec2-app` (Bolt 7): S3 | `GetObject` on `artifacts/app/*`; `Put/Get/DeleteObject` on `uploads/originals/*`; `GetObject` on `uploads/thumbnails/*`, `uploads/meta/*` | Download app zip; store, read and delete user photos; read Lambda output | No, prefix-scoped ARNs |
| `cloudscale-ec2-app`: Secrets Manager | `GetSecretValue` on the RDS master secret ARN | App reads DB credentials at start | No, one ARN |
| `cloudscale-ec2-app`: SSM | `GetParameter(s)` on `parameter/cloudscale/*` | App secret key and config flags | No, path-scoped |
| `cloudscale-ec2-app`: KMS | `kms:Decrypt` with `kms:ViaService = ssm.us-east-1.amazonaws.com` | Decrypt SSM SecureString (default `aws/ssm` key, whose ARN isn't known before first use) | **Yes, `Resource: "*"`**, only usable through SSM |
| `cloudscale-ec2-app`: SNS | `Publish`, `Subscribe` on `claim-notifications` | Email owners when an item is claimed | No, one ARN |
| `cloudscale-ec2-app`: Bedrock | `InvokeModel` on the Nova Micro inference profile and the `amazon.nova-micro-v1:0` foundation-model ARNs in us-east-1/us-east-2/us-west-2 | "Write description" button; the `us.` profile can route to those regions | No, specific ARNs |
| `cloudscale-ec2-app`: SageMaker | `InvokeEndpoint` on endpoint `cloudscale-category` | Category prediction | No, one ARN |
| `cloudscale-ec2-app`: Logs | `CreateLogStream`, `PutLogEvents` on `/cloudscale/app:*` | Application logs | No, one log group |
| `cloudscale-ec2-app`: managed policy | `AmazonSSMManagedInstanceCore` | Session Manager (no SSH) | No (managed policy) |
| Uploads bucket policy (Bolt 2/3b) | `s3:GetObject` on `originals/*` and `thumbnails/*` (superseded in Bolt 5: thumbnails only) for principal `cloudfront.amazonaws.com`, condition `AWS:SourceArn` = the CloudScale distribution | CloudFront serves photos via OAC; the bucket stays private and `meta/` is never exposed | No, specific prefixes and one distribution |
| `cloudscale-sagemaker-exec` (Phase 10): S3 | `GetObject`, `PutObject` on `artifacts/ml/*`; `ListBucket` on the artifacts bucket only for prefix `ml/*` | Read training code and data, write the model artifact | No |
| `cloudscale-sagemaker-exec`: ECR | `BatchCheckLayerAvailability`, `GetDownloadUrlForLayer`, `BatchGetImage` on `sagemaker-scikit-learn` repository | Pull the AWS scikit-learn container | No, one repository |
| `cloudscale-sagemaker-exec`: ECR token | `ecr:GetAuthorizationToken` | Required to authenticate the image pull; the API has no resource-level permissions | **Yes, `Resource: "*"`** |
| `cloudscale-sagemaker-exec`: Logs | `CreateLogGroup`, `CreateLogStream`, `PutLogEvents`, `DescribeLogStreams` on `/aws/sagemaker/*` | Training and endpoint logs | No, SageMaker log groups only |
| `cloudscale-lambda-thumbnailer` (Bolt 5): SQS | `ReceiveMessage`, `DeleteMessage`, `GetQueueAttributes` on queue `image-jobs` | Poll image jobs | No, one queue |
| `cloudscale-lambda-thumbnailer`: S3 | `GetObject` on `uploads/originals/*`; `PutObject` on `uploads/thumbnails/*` and `uploads/meta/*` | Read the original, write thumbnail and analysis | No, prefix-scoped |
| `cloudscale-lambda-thumbnailer`: Rekognition | `DetectLabels`, `DetectModerationLabels` | Auto-tag photos and hide inappropriate ones; Rekognition has no resource-level permissions | **Yes, `Resource: "*"`** |
| `cloudscale-lambda-thumbnailer`: Logs | `CreateLogStream`, `PutLogEvents` on `/aws/lambda/cloudscale-thumbnailer:*` | Function logs | No, one log group |
| SQS queue policy `image-jobs` (Bolt 5) | `sqs:SendMessage` for principal `s3.amazonaws.com`, conditions `aws:SourceArn` = uploads bucket and `aws:SourceAccount` = this account | S3 event notifications | No, one queue, one bucket |
| Uploads bucket policy (updated in Bolt 5) | CloudFront `GetObject` now only on `thumbnails/*` (`originals/*` removed) | Originals and meta are never served publicly; flagged photos never get a thumbnail | No |
