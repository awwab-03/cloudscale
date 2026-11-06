resource "aws_db_subnet_group" "main" {
  name        = "${var.name_prefix}-db-subnets"
  description = "Private DB subnets"
  subnet_ids  = aws_subnet.private_db[*].id

  tags = { Name = "${var.name_prefix}-db-subnets" }
}

resource "aws_db_instance" "main" {
  identifier = "${var.name_prefix}-db"

  engine         = "postgres"
  engine_version = "16.15"
  instance_class = "db.t4g.micro"

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "cloudscale"
  username = "cloudscale_admin"

  # Password generated and stored by RDS in Secrets Manager; never in code or Git.
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period    = 1
  auto_minor_version_upgrade = true
  skip_final_snapshot        = true # so teardown works
  deletion_protection        = false
  apply_immediately          = true

  tags = { Name = "${var.name_prefix}-db" }
}
