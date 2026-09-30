/**
 * Encendido y apagado programado de la base de datos de staging.
 *
 * Cloud SQL es el único recurso del proyecto que no escala a cero. En staging
 * no hace falta que esté disponible de noche ni en fin de semana, y apagarla
 * ahorra cerca de dos terceras partes de su costo.
 *
 * Se implementa con Cloud Scheduler llamando directamente a la API de
 * administración de Cloud SQL. **Sin código propio**: no hay función que
 * mantener, actualizar ni depurar, solo dos trabajos programados y una cuenta
 * de servicio con un permiso.
 */

variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "instance_name" { type = string }

variable "timezone" {
  type    = string
  default = "America/Monterrey"
}

variable "start_cron" {
  type        = string
  default     = "0 7 * * 1-5"
  description = "Encendido: 07:00, de lunes a viernes."
}

variable "stop_cron" {
  type        = string
  default     = "0 21 * * *"
  description = "Apagado: 21:00, todos los días."
}

locals {
  prefix = "narrateca-${var.environment}"
  api_url = format(
    "https://sqladmin.googleapis.com/v1/projects/%s/instances/%s",
    var.project_id,
    var.instance_name,
  )
}

resource "google_service_account" "scheduler" {
  account_id   = "${local.prefix}-sql-horario"
  display_name = "Horario de la base de datos (${var.environment})"
}

# `cloudsql.editor` y no `admin`: puede cambiar la política de activación, no
# borrar la instancia.
resource "google_project_iam_member" "scheduler" {
  project = var.project_id
  role    = "roles/cloudsql.editor"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "start" {
  name        = "${local.prefix}-sql-encender"
  description = "Enciende la base de datos de staging al inicio de la jornada"
  schedule    = var.start_cron
  time_zone   = var.timezone
  region      = var.region

  http_target {
    http_method = "PATCH"
    uri         = local.api_url
    body = base64encode(jsonencode({
      settings = { activationPolicy = "ALWAYS" }
    }))
    headers = {
      "Content-Type" = "application/json"
    }
    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}

resource "google_cloud_scheduler_job" "stop" {
  name        = "${local.prefix}-sql-apagar"
  description = "Apaga la base de datos de staging al terminar la jornada"
  schedule    = var.stop_cron
  time_zone   = var.timezone
  region      = var.region

  http_target {
    http_method = "PATCH"
    uri         = local.api_url
    body = base64encode(jsonencode({
      settings = { activationPolicy = "NEVER" }
    }))
    headers = {
      "Content-Type" = "application/json"
    }
    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}

output "note" {
  value = <<-NOTA
    La base de datos de staging se apaga a las ${var.stop_cron} (${var.timezone})
    y se enciende a las ${var.start_cron}.

    Fuera de ese horario staging responde con error de conexión. No es un fallo:
    para encenderla antes, ejecutar el trabajo `${google_cloud_scheduler_job.start.name}`
    desde la consola de Cloud Scheduler.
  NOTA
}
