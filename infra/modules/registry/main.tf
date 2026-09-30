/**
 * Artifact Registry para las imágenes de contenedor.
 *
 * Con política de limpieza: sin ella, cada despliegue deja una imagen de casi
 * 1,5 GB acumulándose de forma indefinida, y el almacenamiento del registro
 * termina costando más que el cómputo.
 */

variable "project_id" { type = string }
variable "region" { type = string }

variable "keep_recent" {
  type        = number
  default     = 10
  description = "Imágenes recientes que se conservan por repositorio."
}

resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "narrateca"
  format        = "DOCKER"
  description   = "Imágenes de NarraTECa para todos los ambientes"

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "conservar-recientes"
    action = "KEEP"
    most_recent_versions {
      keep_count = var.keep_recent
    }
  }

  cleanup_policies {
    id     = "borrar-antiguas"
    action = "DELETE"
    condition {
      older_than = "2592000s" # 30 días
    }
  }
}

output "repository_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}"
}
