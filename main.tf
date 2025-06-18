terraform {
  required_providers {
    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = "1.15.1"
    }
    google = {
      source  = "hashicorp/google"
      version = "5.34.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.6.2"
    }
  }
}

# --- Provider Configuration ---
provider "mongodbatlas" {
  public_key  = var.atlas_public_key
  private_key = var.atlas_private_key
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# =================================================================
# === WORKFLOW 1: CREATE A NEW PROJECT, CLUSTER, AND 10 USERS   ===
# === (This runs only if `var.create_new_project` is true)       ===
# =================================================================

locals {
  # This local block controls resource creation for the "new project" workflow.
  new_project_workflow_count = var.create_new_project ? 1 : 0
}

# --- Atlas Project Creation ---
resource "mongodbatlas_project" "new_project" {
  count  = local.new_project_workflow_count
  name   = var.new_atlas_project_name
  org_id = var.atlas_org_id
}

# --- Network Infrastructure (First) ---
# 1. Create GCP VPC
resource "google_compute_network" "vpc_for_peering" {
  count                   = local.new_project_workflow_count
  name                    = "atlas-peering-vpc"
  auto_create_subnetworks = true
}

# 2. Create Atlas network container
resource "mongodbatlas_network_container" "vpc_container" {
  count          = local.new_project_workflow_count
  project_id     = mongodbatlas_project.new_project[0].id
  atlas_cidr_block = "10.8.0.0/21"
  provider_name  = "GCP"
  regions        = "US_EAST_1"
}

# 3. Set up the Atlas → GCP peering connection
resource "mongodbatlas_network_peering" "peering_connection" {
  count               = local.new_project_workflow_count
  project_id          = mongodbatlas_project.new_project[0].id
  container_id        = mongodbatlas_network_container.vpc_container[0].container_id
  provider_name       = "GCP"
  gcp_project_id      = var.gcp_project_id
  network_name        = google_compute_network.vpc_for_peering[0].name
}

# 4. Complete the GCP → Atlas peering connection
resource "google_compute_network_peering" "peering_accept" {
  count         = local.new_project_workflow_count
  name          = "gcp-accepts-atlas-peering"
  network       = google_compute_network.vpc_for_peering[0].self_link
  peer_network  = "https://www.googleapis.com/compute/v1/projects/${mongodbatlas_network_peering.peering_connection[0].atlas_gcp_project_id}/global/networks/${mongodbatlas_network_peering.peering_connection[0].atlas_network_name}"
}

# --- Cluster Creation (Only after VPC peering is complete) ---
resource "mongodbatlas_cluster" "new_cluster" {
  count                     = local.new_project_workflow_count
  project_id                = mongodbatlas_project.new_project[0].id
  name                      = var.new_atlas_cluster_name
  provider_name             = "TENANT"
  backing_provider_name     = "GCP"
  provider_instance_size_name = var.new_cluster_tier
  provider_region_name      = "US_EAST_1" # Corresponds to us-east1 in GCP
  
  # Use explicit dependency to ensure VPC peering is complete before cluster creation
  depends_on = [
    google_compute_network_peering.peering_accept,
    mongodbatlas_network_peering.peering_connection
  ]
}

# --- User Creation (10 Users) ---
resource "random_password" "new_user_passwords" {
  count   = var.create_new_project ? 10 : 0
  length  = 16
  special = true
}

resource "mongodbatlas_database_user" "new_cluster_users" {
  count      = var.create_new_project ? 10 : 0
  project_id = mongodbatlas_project.new_project[0].id
  username   = "automated-user-${count.index + 1}"
  password   = random_password.new_user_passwords[count.index].result
  auth_database_name = "admin"
  roles {
    role_name     = "readWriteAnyDatabase"
    database_name = "admin"
  }
  
  # Ensure cluster exists before creating users
  depends_on = [mongodbatlas_cluster.new_cluster]
}

# =================================================================
# === WORKFLOW 2: ADD A SINGLE USER TO THE SOURCE PROJECT       ===
# === (This runs only if `var.create_new_project` is false)     ===
# =================================================================

locals {
  # This local block controls resource creation for the "add user" workflow.
  add_user_workflow_count = var.create_new_project ? 0 : 1
}

# --- Data source to get info about the existing cluster ---
data "mongodbatlas_clusters" "source_project_clusters" {
  count      = local.add_user_workflow_count
  project_id = var.source_project_id
}

# --- User Creation (1 User) ---
resource "random_string" "new_user_suffix" {
  count   = local.add_user_workflow_count
  length  = 8
  special = false
  upper   = false
}

resource "random_password" "single_user_password" {
  count   = local.add_user_workflow_count
  length  = 16
  special = true
}

resource "mongodbatlas_database_user" "single_new_user" {
  count      = local.add_user_workflow_count
  project_id = var.source_project_id
  username   = "new-user-${random_string.new_user_suffix[0].result}"
  password   = random_password.single_user_password[0].result
  auth_database_name = "admin"
  roles {
    role_name     = "readWriteAnyDatabase"
    database_name = "admin"
  }
}

resource "mongodbatlas_project_ip_access_list" "private_ips" {
  count      = local.new_project_workflow_count
  project_id = mongodbatlas_project.new_project[0].id

  for_each = { for ip in var.private_ip_whitelist : ip => ip }

  cidr_block = each.value
  comment    = "Whitelist private IP after VPC peering"
  depends_on = [mongodbatlas_network_peering.peering_connection]
}

