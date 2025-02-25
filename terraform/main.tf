locals {
  service_name  = "${var.resource_suffix}-cosyne-service"
  database_name = "users-${var.resource_suffix}"
}

# Instance Creation
resource "google_spanner_instance" "database_instance" {
  name             = "vmassign-${var.resource_suffix}"
  display_name     = "Assign Instance ${var.resource_suffix}"
  config           = "regional-us-central1"
  processing_units = 100
}


# Database Creation
resource "google_spanner_database" "default" {
  name     = "users"
  instance = google_spanner_instance.database_instance.name
  ddl = [
    "CREATE TABLE Users (Hostname STRING(1024) NOT NULL, Pin STRING(1024), CrdCmd STRING(1024), UserEmail STRING(1024), inUse BOOL,) PRIMARY KEY (Hostname)"
  ]
  deletion_protection = false
}
