/**
 * Ambiente de STAGING.
 *
 * Diferencias deliberadas respecto a producción:
 *
 *   base de datos      nivel mínimo, apagada fuera de horario laboral
 *   protección         sin protección de borrado: se puede recrear entero
 *   copias de respaldo desactivadas
 *   datos              solo contenido sintético, NUNCA material del archivo
 *
 * Esa última línea es una decisión de confidencialidad, no de comodidad: cada
 * copia del material es superficie expuesta, y staging no la necesita.
 */

terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  backend "gcs" {
    # El bucket se pasa con `-backend-config` para no fijar aquí el nombre del
    # proyecto. Ver infra/README.md.
    prefix = "terraform/staging"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" { type = string }
variable "project_number" { type = string }
variable "region" {
  type    = string
  default = "us-central1"
}
variable "github_repository" { type = string }

variable "backend_image" {
  type    = string
  default = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "frontend_image" {
  type    = string
  default = "us-docker.pkg.dev/cloudrun/container/hello"
}

locals {
  environment = "staging"
}

module "cicd" {
  source            = "../../modules/cicd"
  project_id        = var.project_id
  project_number    = var.project_number
  environment       = local.environment
  github_repository = var.github_repository
  allowed_ref       = "refs/heads/main"
}

module "network" {
  source      = "../../modules/network"
  project_id  = var.project_id
  region      = var.region
  environment = local.environment
}

module "database" {
  source                      = "../../modules/database"
  project_id                  = var.project_id
  region                      = var.region
  environment                 = local.environment
  network_id                  = module.network.network_id
  private_services_connection = module.network.private_services_connection

  # El nivel más pequeño disponible: staging no necesita rendimiento.
  tier = "db-f1-micro"

  # Staging es desechable por diseño. Sin protección de borrado, recrearlo
  # entero es una operación normal y no una emergencia.
  deletion_protection = false
  backup_enabled      = false
}

module "scheduler" {
  source        = "../../modules/scheduler"
  project_id    = var.project_id
  region        = var.region
  environment   = local.environment
  instance_name = module.database.instance_name
}

module "registry" {
  source     = "../../modules/registry"
  project_id = var.project_id
  region     = var.region
}

module "storage" {
  source                = "../../modules/storage"
  project_id            = var.project_id
  region                = var.region
  environment           = local.environment
  service_account_email = module.cicd.runtime_email
  force_destroy         = true
}

# --- Secretos ----------------------------------------------------------------

resource "google_secret_manager_secret" "database_url" {
  secret_id = "narrateca-${local.environment}-database-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = module.database.database_url
}

resource "random_password" "session_key" {
  length  = 64
  special = false
}

resource "google_secret_manager_secret" "session_key" {
  secret_id = "narrateca-${local.environment}-secret-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "session_key" {
  secret      = google_secret_manager_secret.session_key.id
  secret_data = random_password.session_key.result
}

# --- Servicios ---------------------------------------------------------------

module "backend" {
  source                = "../../modules/service"
  project_id            = var.project_id
  region                = var.region
  environment           = local.environment
  name                  = "api"
  image                 = var.backend_image
  service_account_email = module.cicd.runtime_email
  network_name          = module.network.network_name
  subnet_name           = module.network.subnet_name

  cpu           = "1"
  memory        = "2Gi"
  max_instances = 2

  env = {
    ENVIRONMENT                  = "staging"
    STORAGE_BACKEND              = "gcs"
    STORAGE_GCS_BUCKET_PUBLIC    = module.storage.public_bucket
    STORAGE_GCS_BUCKET_SENSITIVE = module.storage.sensitive_bucket
    EMBEDDINGS_PROVIDER          = "onnx"
    CORS_ORIGINS                 = module.frontend.url
    SESSION_COOKIE_SAMESITE      = "lax"
  }

  secrets = {
    DATABASE_URL = google_secret_manager_secret.database_url.secret_id
    SECRET_KEY   = google_secret_manager_secret.session_key.secret_id
  }
}

module "frontend" {
  source                = "../../modules/service"
  project_id            = var.project_id
  region                = var.region
  environment           = local.environment
  name                  = "web"
  image                 = var.frontend_image
  service_account_email = module.cicd.runtime_email

  cpu                = "1"
  memory             = "512Mi"
  max_instances      = 2
  startup_probe_path = "/"

  env = {
    NODE_ENV = "production"
  }
}

# --- Salidas -----------------------------------------------------------------

output "backend_url" { value = module.backend.url }
output "frontend_url" { value = module.frontend.url }
output "registry_url" { value = module.registry.repository_url }
output "workload_identity_provider" { value = module.cicd.workload_identity_provider }
output "deployer_service_account" { value = module.cicd.deployer_email }
output "database_instance" { value = module.database.instance_name }
output "horario_base_de_datos" { value = module.scheduler.note }
