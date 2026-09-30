/**
 * PostgreSQL con pgvector en Cloud SQL.
 *
 * Es el **único recurso del proyecto que no escala a cero**, y por tanto el
 * único costo permanente. Por eso el ambiente de staging usa el nivel más
 * pequeño disponible y se apaga fuera de horario laboral (ver el módulo
 * `scheduler`).
 */

variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "network_id" { type = string }
variable "private_services_connection" { type = string }

variable "tier" {
  type        = string
  description = "Nivel de la instancia. `db-f1-micro` para staging."
}

variable "deletion_protection" {
  type    = bool
  default = true
}

variable "backup_enabled" {
  type    = bool
  default = true
}

variable "retained_backups" {
  type    = number
  default = 7
}

locals {
  prefix = "narrateca-${var.environment}"
}

resource "google_sql_database_instance" "main" {
  name             = local.prefix
  database_version = "POSTGRES_16"
  region           = var.region

  # Evita que un `terraform destroy` accidental borre el archivo. En staging se
  # desactiva a propósito, porque ahí solo hay datos sintéticos.
  deletion_protection = var.deletion_protection

  depends_on = [var.private_services_connection]

  settings {
    tier              = var.tier
    availability_type = var.environment == "prod" ? "ZONAL" : "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 10
    disk_autoresize   = true

    ip_configuration {
      # Sin IP pública: la base solo es alcanzable desde la red privada.
      ipv4_enabled    = false
      private_network = var.network_id
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    backup_configuration {
      enabled                        = var.backup_enabled
      start_time                     = "07:00" # UTC, madrugada en México
      point_in_time_recovery_enabled = var.environment == "prod"

      dynamic "backup_retention_settings" {
        for_each = var.backup_enabled ? [1] : []
        content {
          retained_backups = var.retained_backups
          retention_unit   = "COUNT"
        }
      }
    }

    maintenance_window {
      day          = 7 # domingo
      hour         = 8
      update_track = "stable"
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }

    insights_config {
      query_insights_enabled = true
      # No se registran los valores de los parámetros: una consulta puede
      # contener fragmentos de testimonio, y esos no deben acabar en los
      # registros de rendimiento.
      record_application_tags = false
      record_client_address   = false
    }
  }
}

resource "google_sql_database" "main" {
  name     = "narrateca"
  instance = google_sql_database_instance.main.name
}

resource "random_password" "app" {
  length  = 40
  special = true
  # Se excluyen los caracteres que rompen una cadena de conexión al no estar
  # codificados: es una fuente clásica de fallos difíciles de diagnosticar.
  override_special = "!#$%&*-_=+"
}

resource "google_sql_user" "app" {
  name     = "narrateca"
  instance = google_sql_database_instance.main.name
  password = random_password.app.result
}

output "instance_name" { value = google_sql_database_instance.main.name }
output "connection_name" { value = google_sql_database_instance.main.connection_name }
output "private_ip" { value = google_sql_database_instance.main.private_ip_address }
output "database_name" { value = google_sql_database.main.name }
output "user" { value = google_sql_user.app.name }

output "database_url" {
  sensitive = true
  value = format(
    "postgresql+asyncpg://%s:%s@%s:5432/%s",
    google_sql_user.app.name,
    urlencode(random_password.app.result),
    google_sql_database_instance.main.private_ip_address,
    google_sql_database.main.name,
  )
}
