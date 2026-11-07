# ======================= SQS: image jobs + DLQ =======================
resource "aws_sqs_queue" "image_jobs_dlq" {
  name                      = "image-jobs-dlq"
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true

  tags = { Name = "image-jobs-dlq" }
}

resource "aws_sqs_queue" "image_jobs" {
  name                       = "image-jobs"
  visibility_timeout_seconds = 360 # >= 6x the Lambda timeout, per AWS guidance
  message_retention_seconds  = 345600
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.image_jobs_dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Name = "image-jobs" }
}

data "aws_iam_policy_document" "image_jobs_from_s3" {
  statement {
    sid       = "AllowS3UploadsBucketToSend"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.image_jobs.arn]
    principals {
      type        = "Service"
      identifiers = ["s3.amazonaws.com"]
    }
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_s3_bucket.uploads.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_sqs_queue_policy" "image_jobs" {
  queue_url = aws_sqs_queue.image_jobs.id
  policy    = data.aws_iam_policy_document.image_jobs_from_s3.json
}

resource "aws_s3_bucket_notification" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  queue {
    queue_arn     = aws_sqs_queue.image_jobs.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "originals/"
  }

  depends_on = [aws_sqs_queue_policy.image_jobs]
}

# ======================= SNS =======================
# Claim emails: the app publishes with attribute owner_email and subscribes each user's address
# (email protocol, filter policy on owner_email) when they sign in.
resource "aws_sns_topic" "claim_notifications" {
  name = "claim-notifications"
  tags = { Name = "claim-notifications" }
}

# Operations alerts (CloudWatch alarm target). Recipient must click the confirmation link once.
resource "aws_sns_topic" "ops_alerts" {
  name = "ops-alerts"
  tags = { Name = "ops-alerts" }
}

resource "aws_sns_topic_subscription" "ops_alerts_email" {
  topic_arn = aws_sns_topic.ops_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
