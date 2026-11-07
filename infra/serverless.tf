# Thumbnailer Lambda (outside the VPC: it only needs S3, SQS and Rekognition).
# Build the package first: .\scripts\build_lambda.ps1  (creates build/thumbnailer)

data "archive_file" "thumbnailer" {
  type        = "zip"
  source_dir  = "${path.module}/../build/thumbnailer"
  output_path = "${path.module}/../build/thumbnailer.zip"
}

resource "aws_cloudwatch_log_group" "thumbnailer" {
  name              = "/aws/lambda/${var.name_prefix}-thumbnailer"
  retention_in_days = 7
  tags              = { Name = "${var.name_prefix}-thumbnailer-logs" }
}

resource "aws_iam_role" "lambda_thumbnailer" {
  name = "${var.name_prefix}-lambda-thumbnailer"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

data "aws_iam_policy_document" "lambda_thumbnailer" {
  statement {
    sid       = "ConsumeImageJobs"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.image_jobs.arn]
  }

  statement {
    sid       = "ReadOriginals"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.uploads.arn}/originals/*"]
  }

  statement {
    sid     = "WriteThumbnailsAndMeta"
    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.uploads.arn}/thumbnails/*",
      "${aws_s3_bucket.uploads.arn}/meta/*",
    ]
  }

  # Rekognition DetectLabels / DetectModerationLabels do not support resource-level permissions
  # (documented in docs/iam-justification.md).
  statement {
    sid       = "RekognitionImageAnalysis"
    actions   = ["rekognition:DetectLabels", "rekognition:DetectModerationLabels"]
    resources = ["*"]
  }

  statement {
    sid       = "WriteOwnLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.thumbnailer.arn}:*"]
  }
}

resource "aws_iam_role_policy" "lambda_thumbnailer" {
  name   = "${var.name_prefix}-lambda-thumbnailer"
  role   = aws_iam_role.lambda_thumbnailer.id
  policy = data.aws_iam_policy_document.lambda_thumbnailer.json
}

resource "aws_lambda_function" "thumbnailer" {
  function_name    = "${var.name_prefix}-thumbnailer"
  role             = aws_iam_role.lambda_thumbnailer.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.thumbnailer.output_path
  source_code_hash = data.archive_file.thumbnailer.output_base64sha256
  memory_size      = 512
  timeout          = 60

  tags = { Name = "${var.name_prefix}-thumbnailer" }

  depends_on = [aws_cloudwatch_log_group.thumbnailer, aws_iam_role_policy.lambda_thumbnailer]
}

resource "aws_lambda_event_source_mapping" "image_jobs" {
  event_source_arn        = aws_sqs_queue.image_jobs.arn
  function_name           = aws_lambda_function.thumbnailer.arn
  batch_size              = 5
  function_response_types = ["ReportBatchItemFailures"]
}
