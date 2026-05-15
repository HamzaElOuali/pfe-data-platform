# Création du Dataset Bronze
resource "google_bigquery_dataset" "bronze_dataset" {
  dataset_id                  = "pfe_bronze"
  friendly_name               = "Dataset Bronze pour le Streaming"
  description                 = "Données brutes venant de Kafka"
  location                    = var.region
  delete_contents_on_destroy  = true
}
