data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

# ---------- ALB: HTTP only from CloudFront ----------
resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb-sg"
  description = "ALB: HTTP 80 from CloudFront origin-facing prefix list only"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.name_prefix}-alb-sg" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http_cf" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTP from CloudFront"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront.id
}

resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  description                  = "To app instances"
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.app.id
}

# ---------- App ----------
resource "aws_security_group" "app" {
  name        = "${var.name_prefix}-app-sg"
  description = "App: 8000 from ALB only"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.name_prefix}-app-sg" }
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  description                  = "App port from ALB"
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.alb.id
}

resource "aws_vpc_security_group_egress_rule" "app_all" {
  security_group_id = aws_security_group.app.id
  description       = "Outbound (via NAT / S3 endpoint)"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# ---------- DB ----------
resource "aws_security_group" "db" {
  name        = "${var.name_prefix}-db-sg"
  description = "DB: 5432 from app-sg only"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.name_prefix}-db-sg" }
}

resource "aws_vpc_security_group_ingress_rule" "db_from_app" {
  security_group_id            = aws_security_group.db.id
  description                  = "Postgres from app"
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.app.id
}

# ---------- NAT ----------
resource "aws_security_group" "nat" {
  name        = "${var.name_prefix}-nat-sg"
  description = "NAT instance: all inbound only from private app subnets"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.name_prefix}-nat-sg" }
}

resource "aws_vpc_security_group_ingress_rule" "nat_from_private_app" {
  count             = 2
  security_group_id = aws_security_group.nat.id
  description       = "All traffic from private app subnet ${count.index}"
  ip_protocol       = "-1"
  cidr_ipv4         = var.private_app_subnet_cidrs[count.index]
}

resource "aws_vpc_security_group_egress_rule" "nat_all" {
  security_group_id = aws_security_group.nat.id
  description       = "All outbound"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}
