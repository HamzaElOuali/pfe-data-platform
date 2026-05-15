variable "project_id" {
  description = "L'ID de votre projet GCP"
  type        = string
  default     = "pfe-data-platform-cloud"
}

variable "region" {
  description = "Région GCP"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zone GCP"
  type        = string
  default     = "us-central1-a"
}

variable "bucket_name" {
  description = "Nom unique du bucket GCS pour Spark"
  type        = string
  default     = "pfe-spark-checkpoints-data"
}
