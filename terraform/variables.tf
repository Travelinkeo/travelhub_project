variable "project_id" {
  description = "El ID del proyecto de Google Cloud (ej. travelhub-468322)"
  type        = string
}

variable "region" {
  description = "Región principal para los recursos (ej. us-central1)"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zona específica (ej. us-central1-a)"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Entorno de despliegue (prod, staging, dev)"
  type        = string
  validation {
    condition     = contains(["prod", "staging", "dev"], var.environment)
    error_message = "El environment debe ser prod, staging, o dev."
  }
}

variable "db_tier" {
  description = "Tipo de máquina para Cloud SQL"
  type        = string
  default     = "db-custom-2-4096" # 2 vCPU, 4GB RAM
}
