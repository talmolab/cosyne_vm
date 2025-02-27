terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.5.0"
    }
  }
}

provider "google" {
  project                     = "vmassign-dev"
  region                      = "us-west1"
  impersonate_service_account = "github-actions-testing@vmassign-dev.iam.gserviceaccount.com"
}
