provider "aws" {
  region = "eu-west-2"
}

data "aws_subnet" "public_subnet" {
  filter {
    name   = "tag:Name"
    values = ["c16-public-subnet-1"]
  }
}

data "aws_security_group" "sg_toby" {
  name = "C16-toby-ec2-sg"
}

resource "aws_instance" "my_ec2_server" {
  ami           = "ami-00710ab5544b60cf7"
  instance_type = "t2.micro"
  subnet_id     = data.aws_subnet.public_subnet.id
  associate_public_ip_address = true

  key_name = "c16-toby-hayman-key-pair"
  security_groups = [data.aws_security_group.sg_toby.id]

  tags = {
    Name = "c16_toby_ec2"
  }
}