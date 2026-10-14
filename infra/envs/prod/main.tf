/**
 * Ambiente de PRODUCCIÓN.
 *
 * Diferencias deliberadas respecto a staging:
 *
 *   base de datos      nivel con recursos dedicados, encendida siempre
 *   protección         protección de borrado activa en la base y en los servicios
 *   copias             diarias, con recuperación a un punto en el tiempo
 *   despliegue         solo desde una etiqueta de versión, nunca desde `main`
 *
 * Aquí vive el material del archivo. Cada una de esas diferencias existe para
 * que un error de operación no pueda destruirlo.
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
    prefix = "terraform/prod"
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
  environment = "prod"
}

module "cicd" {
  source            = "../../modules/cicd"
  project_id        = var.project_id
  project_number    = var.project_number
  environment       = local.environment
  github_repository = var.github_repository

  # Solo una etiqueta de versión despliega a producción. Un push a `main` no
  # basta: eso es lo que separa «lo que el equipo está construyendo» de «lo que
  # el público está viendo».
  allowed_ref = "refs/tags/*"
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

  # Recursos dedicados, no compartidos: el rendimiento de la búsqueda vectorial
  # depende de tener memoria propia.
  tier = "db-custom-1-3840"

  deletion_protection = true
  backup_enabled      = true
  retained_backups    = 14
}

# Sin módulo `scheduler`: producción no se apaga.

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

  # Nunca se destruye un bucket con material del archivo dentro.
  force_destroy = false
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

# El proveedor de modelo de lenguaje. Se crea vacío: la credencial la carga una
# persona, no Terraform, para que no quede en el estado.
resource "google_secret_manager_secret" "llm_api_key" {
  secret_id = "narrateca-${local.environment}-llm-api-key"
  replication {
    auto {}
  }
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

  cpu           = "2"
  memory        = "4Gi"
  max_instances = 10

  env = {
    ENVIRONMENT                  = "production"
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
    LLM_API_KEY  = google_secret_manager_secret.llm_api_key.secret_id
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
  memory             = "1Gi"
  max_instances      = 10
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
