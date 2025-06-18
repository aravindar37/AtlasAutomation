variable "atlas_public_key" {
  description = "Public key for the Atlas Admin API."
  type        = string
  sensitive   = true
}

variable "atlas_private_key" {
  description = "Private key for the Atlas Admin API."
  type        = string
  sensitive   = true
}

variable "atlas_org_id" {
  description = "The ID of the Atlas Organization where new projects will be created."
  type        = string
}

variable "source_project_id" {
  description = "The ID of the source Atlas project to check for user count."
  type        = string
}

variable "gcp_project_id" {
  description = "The GCP Project ID where the VPC will be created for peering."
  type        = string
}

variable "gcp_region" {
  description = "The GCP region for the VPC and the Atlas cluster."
  type        = string
  default     = "us-east1"
}

variable "new_atlas_project_name" {
  description = "The name for the new Atlas project if created."
  type        = string
  default     = "New-Automated-Project"
}

variable "new_atlas_cluster_name" {
  description = "The name for the new Atlas cluster if created."
  type        = string
  default     = "automated-cluster"
}

variable "new_cluster_tier" {
  description = "The instance size for the new cluster."
  type        = string
  default     = "M10"
}

variable "create_new_project" {
  description = "A boolean flag to control the workflow. True to create a new project, false to add a user to the source project."
  type        = bool
}
variable "private_ip_whitelist" {
  description = "List of private IP addresses to whitelist for the new cluster."
  type        = list(string)
  default     = ["10.8.0.10/32", "10.8.0.11/32"]
}