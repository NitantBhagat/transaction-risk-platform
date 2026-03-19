terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration (state storage) should be provided by the
  # deploying environment (e.g. S3 + DynamoDB). Example:
  #
  # backend "s3" {
  #   bucket         = "your-tf-state-bucket"
  #   key            = "transaction-risk-platform/terraform.tfstate"
  #   region         = "eu-west-1"
  #   dynamodb_table = "your-tf-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region
}

locals {
  project     = var.project
  environment = var.environment

  common_tags = {
    Project     = local.project
    Environment = local.environment
    ManagedBy   = "terraform"
  }
}

# Service-specific infrastructure (API Gateway, ECS/EKS, RDS, Redis, etc.)
# will be added as modules or resources in later steps.

