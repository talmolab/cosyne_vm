variable "project_id" {
  description = "Target Project ID"
  type        = string
  default     = "vmassign-dev"
}

variable "resource_suffix" {
  description = "Suffix to append to all resources"
  type        = string
  default     = "test"
}
