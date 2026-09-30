/**
 * Red privada para que Cloud Run alcance Cloud SQL sin exponerlo a internet.
 *
 * Se usa **salida directa a VPC** y no un conector serverless. Un conector
 * mantiene instancias encendidas de forma permanente aunque no haya tráfico,
 * lo que contradice la decisión de no dejar recursos ociosos (design.md,
 * decisión 15). La salida directa no tiene ese costo base.
 */

variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }

locals {
  prefix = "narrateca-${var.environment}"
}

resource "google_compute_network" "main" {
  name                    = local.prefix
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = local.prefix
  network       = google_compute_network.main.id
  region        = var.region
  ip_cidr_range = "10.20.0.0/24"

  # Necesario para que Cloud Run use salida directa a esta subred.
  purpose = "PRIVATE"

  private_ip_google_access = true
}

# Rango reservado para las direcciones privadas de los servicios gestionados
# de Google, entre ellos Cloud SQL.
resource "google_compute_global_address" "private_services" {
  name          = "${local.prefix}-servicios-privados"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main.id
}

resource "google_service_networking_connection" "private_services" {
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services.name]
}

output "network_id" { value = google_compute_network.main.id }
output "network_name" { value = google_compute_network.main.name }
output "subnet_id" { value = google_compute_subnetwork.main.id }
output "subnet_name" { value = google_compute_subnetwork.main.name }
output "private_services_connection" { value = google_service_networking_connection.private_services.id }
