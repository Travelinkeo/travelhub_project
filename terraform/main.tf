terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  # Backend para almacenar el estado de Terraform en Cloud Storage.
  # Inicializar con: terraform init -backend-config=backend.hcl
  # (El bucket no se hardcodea aquí para no exponer credenciales en el repo)
  backend "gcs" {
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# --- RECURSOS BASE (EJEMPLO ARQUITECTURA SILICON VALLEY) ---

# 1. Base de Datos Cloud SQL (PostgreSQL)
resource "google_sql_database_instance" "postgres_primary" {
  name             = "travelhub-db-primary-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = var.db_tier
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
    }

    ip_configuration {
      ipv4_enabled    = false # Privado por defecto
      private_network = google_compute_network.vpc.id
    }
  }

  deletion_protection = var.environment == "prod" ? true : false
}

# 2. VPC y Subredes
resource "google_compute_network" "vpc" {
  name                    = "travelhub-vpc-${var.environment}"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "travelhub-subnet-${var.environment}"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
}

# 3. Google Kubernetes Engine (GKE) o Cloud Run
# Para TravelHub recomendaremos Cloud Run inicial para agilidad y auto-escalado
resource "google_cloud_run_v2_service" "travelhub_api" {
  name     = "travelhub-api-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "gcr.io/${var.project_id}/travelhub-api:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      # Secrets inyectados desde Secret Manager
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_url.secret_id
            version = "latest"
          }
        }
      }

      # Variables normales
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
    }
    scaling {
      min_instance_count = var.environment == "prod" ? 2 : 0
      max_instance_count = 10
    }
  }
}

# 4. Secret Manager (Gestión de Secretos)
resource "google_secret_manager_secret" "db_url" {
  secret_id = "database_url_${var.environment}"

  replication {
    auto {}
  }
}
