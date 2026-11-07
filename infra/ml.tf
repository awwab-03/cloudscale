# SageMaker execution role for the category-model training job and serverless endpoint.
# The training job, model, endpoint config and endpoint themselves are created by ml/*.py
# (so they can be re-run and deleted by scripts/teardown); this file only owns the IAM role.

locals {
  sagemaker_sklearn_repo_arn = "arn:aws:ecr:${var.region}:683313688378:repository/sagemaker-scikit-learn"
}

resource "aws_iam_role" "sagemaker_exec" {
  name = "${var.name_prefix}-sagemaker-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

data "aws_iam_policy_document" "sagemaker_exec" {
  statement {
    sid       = "ReadWriteMlPrefixOnly"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.artifacts.arn}/ml/*"]
  }

  statement {
    sid       = "ListMlPrefixOnly"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.artifacts.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["ml/*"]
    }
  }

  # ecr:GetAuthorizationToken does not support resource-level permissions (documented in docs/iam-justification.md).
  statement {
    sid       = "EcrAuthToken"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "PullSklearnImageOnly"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
    ]
    resources = [local.sagemaker_sklearn_repo_arn]
  }

  statement {
    sid = "SageMakerLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
    ]
    resources = [
      "arn:aws:logs:${var.region}:${local.account_id}:log-group:/aws/sagemaker/*",
      "arn:aws:logs:${var.region}:${local.account_id}:log-group:/aws/sagemaker/*:log-stream:*",
    ]
  }
}

resource "aws_iam_role_policy" "sagemaker_exec" {
  name   = "${var.name_prefix}-sagemaker-exec"
  role   = aws_iam_role.sagemaker_exec.id
  policy = data.aws_iam_policy_document.sagemaker_exec.json
}
