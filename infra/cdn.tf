# AWS managed policies (fixed IDs)
locals {
  cf_caching_disabled  = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
  cf_caching_optimized = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  cf_all_viewer        = "216adef6-5c7f-47e4-b989-5492eafa07d3"
}

resource "aws_cloudfront_origin_access_control" "uploads" {
  name                              = "${var.name_prefix}-uploads-oac"
  description                       = "CloudFront to uploads bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# /media/originals/x.jpg -> S3 key originals/x.jpg
resource "aws_cloudfront_function" "strip_media" {
  name    = "${var.name_prefix}-strip-media-prefix"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-EOT
    function handler(event) {
      var request = event.request;
      request.uri = request.uri.replace(/^\/media/, '');
      return request;
    }
  EOT
}

resource "aws_cloudfront_distribution" "main" {
  enabled         = true
  comment         = "CloudScale Lost & Found"
  is_ipv6_enabled = true
  price_class     = "PriceClass_100"

  origin {
    origin_id   = "alb"
    domain_name = aws_lb.app.dns_name

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }

    custom_header {
      name  = "X-Origin-Verify"
      value = random_password.origin_verify.result
    }
  }

  origin {
    origin_id                = "uploads"
    domain_name              = aws_s3_bucket.uploads.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.uploads.id
  }

  default_cache_behavior {
    target_origin_id         = "alb"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    compress                 = true
    cache_policy_id          = local.cf_caching_disabled
    origin_request_policy_id = local.cf_all_viewer
  }

  ordered_cache_behavior {
    path_pattern           = "/media/*"
    target_origin_id       = "uploads"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = local.cf_caching_optimized

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.strip_media.arn
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = { Name = "${var.name_prefix}-cdn" }
}
