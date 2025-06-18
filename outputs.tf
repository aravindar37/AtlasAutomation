output "workflow_executed" {
  value = var.create_new_project ? "new_project_created" : "single_user_added"
}

output "new_project_connection_string" {
  description = "The connection string for the newly created cluster."
  value       = var.create_new_project ? mongodbatlas_cluster.new_cluster[0].connection_strings[0].standard_srv : "N/A"
}

output "new_project_users" {
  description = "List of users created in the new project."
  value       = var.create_new_project ? [for user in mongodbatlas_database_user.new_cluster_users : { username = user.username, password = user.password }] : []
  sensitive   = true
}

output "single_user_details" {
  description = "Details for the single user added to the source project."
  value = !var.create_new_project ? {
    username                = mongodbatlas_database_user.single_new_user[0].username,
    password                = mongodbatlas_database_user.single_new_user[0].password,
    connection_string       = data.mongodbatlas_clusters.source_project_clusters[0].results[0].connection_strings[0].standard_srv
    } : {}
  sensitive = true
}