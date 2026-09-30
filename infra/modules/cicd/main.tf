/**
 * Autenticación de GitHub Actions contra GCP mediante Workload Identity
 * Federation.
 *
 * **No se genera ninguna llave.** GitHub presenta un token firmado por su
 * propio emisor, GCP lo verifica y entrega credenciales de vida corta. La
 * alternativa —guardar una llave JSON de cuenta de servicio como secreto del
 * repositorio— crea una credencial de larga vida que, si se filtra, entrega el
 * proyecto entero y no caduca sola.
 *
 * La condición de atributo es lo que sostiene la seguridad del arreglo: sin
 * ella, **cualquier repositorio de GitHub** podría pedir estas credenciales.
 */

variable "project_id" { type = string }
variable "project_number" { type = string }
variable "environment" { type = string }

variable "github_repository" {
  type        = string
  description = "Repositorio en formato `organizacion/repositorio`."
}

variable "allowed_ref" {
  type        = string
  description = <<-DESC
    Referencia de git autorizada a desplegar a este ambiente.
    Staging: `refs/heads/main`. Producción: `refs/tags/*`.
  DESC
}

locals {
  prefix = "narrateca-${var.environment}"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "${local.prefix}-github"
  display_name              = "GitHub Actions (${var.environment})"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Sin esta condición, cualquier repositorio de GitHub del mundo podría
  # obtener credenciales de este proyecto.
  attribute_condition = "assertion.repository == '${var.github_repository}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "deployer" {
  account_id   = "${local.prefix}-deploy"
  display_name = "Despliegue de NarraTECa (${var.environment})"
}

# Solo la referencia autorizada puede suplantar la cuenta de despliegue. En
# producción eso significa que un push a `main` no despliega: hace falta una
# etiqueta de versión.
resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member = format(
    "principalSet://iam.googleapis.com/projects/%s/locations/global/workloadIdentityPools/%s/attribute.repository/%s",
    var.project_number,
    google_iam_workload_identity_pool.github.workload_identity_pool_id,
    var.github_repository,
  )
}

# Permisos de la cuenta de despliegue. Se listan uno a uno en lugar de usar
# `roles/editor`: el despliegue no necesita poder borrar la base de datos.
resource "google_project_iam_member" "deployer" {
  for_each = toset([
    "roles/run.developer",           # desplegar revisiones de Cloud Run
    "roles/artifactregistry.writer", # subir imágenes
    "roles/iam.serviceAccountUser",  # asignar la cuenta de ejecución al servicio
    "roles/cloudsql.client",         # ejecutar migraciones
    "roles/secretmanager.secretAccessor",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# --- Cuenta de ejecución de los servicios ------------------------------------

resource "google_service_account" "runtime" {
  account_id   = "${local.prefix}-run"
  display_name = "Ejecución de NarraTECa (${var.environment})"
}

resource "google_project_iam_member" "runtime" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

output "workload_identity_provider" {
  value = format(
    "projects/%s/locations/global/workloadIdentityPools/%s/providers/%s",
    var.project_number,
    google_iam_workload_identity_pool.github.workload_identity_pool_id,
    google_iam_workload_identity_pool_provider.github.workload_identity_pool_provider_id,
  )
  description = "Valor para `workload_identity_provider` en la acción de autenticación."
}

output "deployer_email" { value = google_service_account.deployer.email }
output "runtime_email" { value = google_service_account.runtime.email }
