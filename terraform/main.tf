terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Fixture-only module: private bucket intent for infrastructure lane materials.
variable "bucket_name" {
  type        = string
  description = "Customer export bucket name"
  default     = "ovk-consumer-customer-exports"
}

resource "aws_s3_bucket" "customer_exports" {
  bucket = var.bucket_name
  tags = {
    sensitivity = "confidential"
    ovk_lane    = "infrastructure"
  }
}

resource "aws_s3_bucket_public_access_block" "customer_exports" {
  bucket                  = aws_s3_bucket.customer_exports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
