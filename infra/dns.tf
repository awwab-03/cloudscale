# Route 53 (Plan B): no registrar domain could be obtained for free, so the public hosted zone
# exists and resolves, but is not delegated from a registrar. Resolution is demonstrated by
# querying the zone's own name servers (see docs/aidlc/phase-8-monitoring-dns.md).

variable "dns_zone_name" {
  description = "Name of the public hosted zone (Plan B: not a registered domain)."
  type        = string
  default     = "cloudscale-lf.example"
}

resource "aws_route53_zone" "main" {
  name    = var.dns_zone_name
  comment = "CloudScale Lost & Found (Plan B: queried directly via its own name servers)"

  tags = { Name = "${var.name_prefix}-zone" }
}

# CloudFront alias targets always use this fixed hosted zone ID.
locals {
  cloudfront_hosted_zone_id = "Z2FDTNDATAQYW2"
}

resource "aws_route53_record" "app_a" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "app.${var.dns_zone_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = local.cloudfront_hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "app_aaaa" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "app.${var.dns_zone_name}"
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = local.cloudfront_hosted_zone_id
    evaluate_target_health = false
  }
}

output "dns_zone_name_servers" {
  value = aws_route53_zone.main.name_servers
}

output "dns_app_record" {
  value = "app.${var.dns_zone_name}"
}
