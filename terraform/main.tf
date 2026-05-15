provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# 1. Bucket GCS pour les Checkpoints Spark et données temporaires
resource "google_storage_bucket" "spark_bucket" {
  name     = var.bucket_name
  location = var.region
  force_destroy = true
  uniform_bucket_level_access = true
}

# 2. IP Statique pour la VM Kafka
resource "google_compute_address" "kafka_static_ip" {
  name = "kafka-static-ip"
}

# 3. La VM Compute Engine (Kafka + Spark)
resource "google_compute_instance" "kafka_spark_vm" {
  name         = "pfe-streaming-vm"
  machine_type = "e2-medium"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 20
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.kafka_static_ip.address
    }
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose python3-pip
    sudo systemctl start docker
    sudo systemctl enable docker
  EOT

  service_account {
    email  = google_service_account.spark_sa.email
    scopes = ["cloud-platform"]
  }

  tags = ["kafka-server"]
}

# 4. Firewall pour ouvrir le port 9092 de Kafka
resource "google_compute_firewall" "allow_kafka" {
  name    = "allow-kafka-ingress"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["9092"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["kafka-server"]
}
