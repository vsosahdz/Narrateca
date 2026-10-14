/**
 * Servicio de Cloud Run parametrizable.
 *
 * Sirve tanto al backend como al frontend. Dos propiedades no son negociables:
 *
 * - `min_instance_count = 0`: ningún recurso de cómputo queda encendido sin
 *   tráfico (design.md, decisión 15). El precio es el arranque en frío, y por
 *   eso las imágenes están optimizadas para arrancar rápido.
 * - Salida **directa** a VPC, no conector serverless: un conector mantiene
 *   instancias encendidas de forma permanente, que es justo lo que se evita.
 */

variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "name" { type = string }
variable "image" { type = string }
variable "service_account_email" { type = string }

variable "subnet_name" {
  type    = string
  default = null
}

variable "network_name" {
  type    = string
  default = null
}

variable "env" {
  type        = map(string)
  default     = {}
  description = "Variables de entorno en claro. Nunca secretos."
}

variable "secrets" {
  type        = map(string)
  default     = {}
  description = "Variable de entorno => nombre del secreto en Secret Manager."
}

variable "cpu" {
  type    = string
  default = "1"
}

variable "memory" {
  type    = string
  default = "2Gi"
}

variable "max_instances" {
  type    = number
  default = 4
}

variable "allow_public" {
  type    = bool
  default = true
}

variable "startup_probe_path" {
  type        = string
  default     = "/ready"
  description = <<-DESC
    Ruta de la sonda de arranque. Por defecto `/ready`, que comprueba la base de
    datos: un proceso vivo que no alcanza su base responde 200 en `/health` y
    recibiría tráfico que solo puede fallar. El frontend no tiene dependencias
    que comprobar y usa `/`.
  DESC
}

locals {
  service_name = "narrateca-${var.name}-${var.environment}"
  uses_vpc     = var.subnet_name != null
}

resource "google_cloud_run_v2_service" "main" {
  name     = local.service_name
  location = var.region

  # El tráfico entra por internet; la protección está en la aplicación, que
  # verifica sesión y rol en cada endpoint de administración.
  ingress = "INGRESS_TRAFFIC_ALL"

  deletion_protection = var.environment == "prod"

  template {
    service_account = var.service_account_email

    scaling {
      # Cero instancias en reposo. Es la decisión de costo del proyecto.
      min_instance_count = 0
      max_instance_count = var.max_instances
    }

    dynamic "vpc_access" {
      for_each = local.uses_vpc ? [1] : []
      content {
        network_interfaces {
          network    = var.network_name
          subnetwork = var.subnet_name
        }
        # Solo el tráfico privado sale por la VPC. El resto —por ejemplo la
        # llamada al proveedor de modelo de lenguaje— sale directo, sin pagar
        # NAT ni añadir un salto.
        egress = "PRIVATE_RANGES_ONLY"
      }
    }

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        # La CPU solo se asigna mientras se atiende una petición: fuera de eso
        # no se factura.
        cpu_idle          = true
        startup_cpu_boost = true
      }

      ports {
        container_port = 8080
      }

      dynamic "env" {
        for_each = var.env
        content {
          name  = env.key
          value = env.value
        }
      }

      # Los secretos se inyectan por referencia a Secret Manager. Nunca como
      # variable en claro: el valor no aparece en el estado de Terraform ni en
      # la descripción del servicio.
      dynamic "env" {
        for_each = var.secrets
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }

      startup_probe {
        http_get {
          path = var.startup_probe_path
        }
        # El backend carga un modelo de embeddings al arrancar. Un margen corto
        # haría que Cloud Run matara instancias sanas durante el arranque.
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 5
        failure_threshold     = 12
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.allow_public ? 1 : 0
  location = google_cloud_run_v2_service.main.location
  name     = google_cloud_run_v2_service.main.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "url" { value = google_cloud_run_v2_service.main.uri }
output "name" { value = google_cloud_run_v2_service.main.name }
