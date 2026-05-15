# 1. Création du compte de service Spark
resource "google_service_account" "spark_sa" {
  account_id   = "sa-spark-streaming"
  display_name = "SA pour Spark Structured Streaming"
}

# 2. Rôle Data Editor sur BigQuery
resource "google_project_iam_member" "bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.spark_sa.email}"
}

# 3. Rôle Job User sur BigQuery
resource "google_project_iam_member" "bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.spark_sa.email}"
}

# 4. Rôle Admin sur le Storage
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.spark_sa.email}"
}
