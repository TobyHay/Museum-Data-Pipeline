provider "aws" {
  region = "eu-west-2"
}

data "aws_vpc" "c16_vpc" {
  id = "vpc-0f7ba8057a52dd82d"
}

resource "aws_security_group" "c16_sg_toby" {
  name        = "c16_sg_toby"
  description = "Sg for Database"
  vpc_id      = data.aws_vpc.c16_vpc.id

  ingress {
    from_port        = 5432
    to_port          = 5432
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    from_port        = 0
    to_port          = 65525
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}


resource "aws_db_instance" "museum-db" {
  allocated_storage            = 10
  db_name                      = "museum"
  identifier                   = "c16-toby-museum"
  engine                       = "postgres"
  engine_version               = "17.2"
  instance_class               = "db.t3.micro"
  publicly_accessible          = true
  performance_insights_enabled = false
  skip_final_snapshot          = true
  db_subnet_group_name         = "c16-public-subnet-group"
  vpc_security_group_ids       = [aws_security_group.c16_sg_toby.id]
  username                     = var.db_username
  password                     = var.db_password
}