variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "kinesis_stream_name" {
  type    = string
  default = "authpulse-dev-stream"
}

variable "lakehouse_bucket_name" {
  type    = string
  default = "authpulse-dev-lakehouse"
}

variable "tags" {
  type = map(string)
  default = {
    project = "authpulse"
    env     = "dev"
  }
}
