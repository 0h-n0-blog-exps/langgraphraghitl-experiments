# [DEBUG] ============================================================
# Agent   : architect
# Task    : Terraform + Docker + docker-compose 設定
# Created : 2026-02-23T18:56:02
# Updated : 2026-02-23T19:10:00
# [/DEBUG] ===========================================================

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # CI/CD やローカル検証 (terraform plan -backend=false) 時の認証スキップ設定。
  # 実際のデプロイでは AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY を設定してください。
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  default_tags {
    tags = {
      project    = var.project_name
      managed_by = "terraform"
    }
  }
}
