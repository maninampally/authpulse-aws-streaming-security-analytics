# Uncomment and configure for remote state in real deployments.
# terraform {
#   backend "s3" {
#     bucket         = "<state-bucket>"
#     key            = "authpulse/prod/terraform.tfstate"
#     region         = "us-east-1"
#     dynamodb_table = "<lock-table>"
#     encrypt        = true
#   }
# }
