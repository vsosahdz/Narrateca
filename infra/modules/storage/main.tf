/**
 * Almacenamiento del material multimedia, separado por sensibilidad.
 *
 * Son **dos buckets distintos y no dos carpetas**: si la separación viviera
 * solo dentro de un bucket, un permiso mal puesto expondría el material
 * sensible por estar mezclado con el resto. Con buckets separados, el de
 * material sensible nunca tiene acceso público que revocar.
 */

variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "service_account_email" { type = string }

variable "force_destroy" {
  type        = bool
  default     = false
  description = "Solo en staging: permite destruir el bucket con contenido."
}

locals {
  prefix = "narrateca-${var.environment}"
}

# --- Material de difusión general -------------------------------------------

resource "google_storage_bucket" "public" {
  name                        = "${local.prefix}-publico"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy

  versioning { enabled = true }

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["Content-Type", "Range"]
    max_age_seconds = 3600
  }
}

resource "google_storage_bucket_iam_member" "public_read" {
  bucket = google_storage_bucket.public.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# --- Material sensible -------------------------------------------------------

resource "google_storage_bucket" "sensitive" {
  name                        = "${local.prefix}-sensible"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy

  # Se conservan versiones anteriores: el archivo es irreemplazable y una
  # sobrescritura accidental no debe ser definitiva.
  versioning { enabled = true }

  # Deliberadamente sin bloque `cors` y sin ningún permiso para `allUsers`.
  # Este material solo se alcanza por URL firmada emitida por el backend, que
  # antes verifica que la pieza esté publicada.

  public_access_prevention = "enforced"
}

# --- Acceso del servicio -----------------------------------------------------

resource "google_storage_bucket_iam_member" "app_public" {
  bucket = google_storage_bucket.public.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.service_account_email}"
}

resource "google_storage_bucket_iam_member" "app_sensitive" {
  bucket = google_storage_bucket.sensitive.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.service_account_email}"
}

output "public_bucket" { value = google_storage_bucket.public.name }
output "sensitive_bucket" { value = google_storage_bucket.sensitive.name }
output "public_base_url" { value = "https://storage.googleapis.com/${google_storage_bucket.public.name}" }
