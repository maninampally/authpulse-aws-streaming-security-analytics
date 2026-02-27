variable "database_name" {
  type        = string
  description = "Glue catalog database name."
  default     = "authpulse"
}

variable "lakehouse_bucket_name" {
  type        = string
  description = "S3 bucket name that holds all Iceberg table data and metadata."
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to all Glue resources."
  default     = {}
}
