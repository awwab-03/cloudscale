data "aws_ssm_parameter" "al2023_x86" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# Shared secret between CloudFront and the ALB (defense in depth). Lives only in local, gitignored state.
resource "random_password" "origin_verify" {
  length  = 40
  special = false
}

# Load-test switch for /api/stress. Toggle with the AWS CLI; Terraform ignores later value changes.
resource "aws_ssm_parameter" "enable_stress" {
  name  = "/cloudscale/enable-stress"
  type  = "String"
  value = "false"

  lifecycle {
    ignore_changes = [value]
  }
}

# ======================= Launch template =======================
resource "aws_launch_template" "app" {
  name                   = "${var.name_prefix}-app"
  image_id               = data.aws_ssm_parameter.al2023_x86.value
  instance_type          = var.app_instance_type
  update_default_version = true

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2_app.name
  }

  vpc_security_group_ids = [aws_security_group.app.id]

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 8
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh.tpl", {
    region            = var.region
    app_version       = var.app_version
    artifacts_bucket  = aws_s3_bucket.artifacts.bucket
    uploads_bucket    = aws_s3_bucket.uploads.bucket
    db_host           = aws_db_instance.main.address
    db_name           = aws_db_instance.main.db_name
    db_secret_arn     = local.rds_secret_arn
    cognito_pool_id   = aws_cognito_user_pool.main.id
    cognito_client_id = aws_cognito_user_pool_client.app.id
    claim_topic_arn   = local.claim_topic_arn
  }))

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name    = "${var.name_prefix}-app"
      Project = "CloudScale"
    }
  }

  tag_specifications {
    resource_type = "volume"
    tags = {
      Name    = "${var.name_prefix}-app"
      Project = "CloudScale"
    }
  }
}

# ======================= ALB =======================
resource "aws_lb" "app" {
  name                       = "${var.name_prefix}-alb"
  load_balancer_type         = "application"
  internal                   = false
  security_groups            = [aws_security_group.alb.id]
  subnets                    = aws_subnet.public[*].id
  drop_invalid_header_fields = true

  tags = { Name = "${var.name_prefix}-alb" }
}

resource "aws_lb_target_group" "app" {
  name                 = "${var.name_prefix}-tg"
  port                 = 8000
  protocol             = "HTTP"
  vpc_id               = aws_vpc.main.id
  deregistration_delay = 30

  health_check {
    path                = "/health"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = { Name = "${var.name_prefix}-tg" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  # Anything without the CloudFront secret header is refused.
  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Forbidden"
      status_code  = "403"
    }
  }
}

resource "aws_lb_listener_rule" "from_cloudfront" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }

  condition {
    http_header {
      http_header_name = "X-Origin-Verify"
      values           = [random_password.origin_verify.result]
    }
  }
}

# ======================= Auto Scaling =======================
resource "aws_autoscaling_group" "app" {
  name                      = "${var.name_prefix}-asg"
  min_size                  = 2
  desired_capacity          = 2
  max_size                  = 4
  vpc_zone_identifier       = aws_subnet.private_app[*].id
  target_group_arns         = [aws_lb_target_group.app.arn]
  health_check_type         = "ELB"
  health_check_grace_period = 300

  launch_template {
    id      = aws_launch_template.app.id
    version = aws_launch_template.app.latest_version
  }

  # Changing app_version updates the launch template, which starts a rolling refresh.
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup        = 120
    }
  }

  tag {
    key                 = "Project"
    value               = "CloudScale"
    propagate_at_launch = true
  }

  # Instances need the NAT route (package install), the DB and the role policy before they boot.
  depends_on = [
    aws_route.private_app_nat,
    aws_db_instance.main,
    aws_iam_role_policy.ec2_app,
    aws_vpc_endpoint.s3,
  ]
}

resource "aws_autoscaling_policy" "cpu" {
  name                   = "${var.name_prefix}-cpu-target-50"
  autoscaling_group_name = aws_autoscaling_group.app.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 50
  }
}
