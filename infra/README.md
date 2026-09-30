# Infraestructura

Dos ambientes en GCP, declarados con Terraform y desplegados con GitHub Actions.

```
   staging                              producción
   ───────                              ──────────
   fusión a main → despliegue           etiqueta v* → despliegue
   base mínima, apagada de noche        base dedicada, siempre encendida
   sin copias de seguridad              copias diarias + punto en el tiempo
   sin protección de borrado            protección activa
   SOLO datos sintéticos                material del archivo
```

## Lo que cuesta

Casi todo escala a cero. La excepción es Cloud SQL, y por eso staging se apaga.

| Recurso | En reposo |
|---|---|
| Cloud Run (4 servicios) | cero: `min_instances = 0` |
| Cloud Storage | por GB almacenado |
| Artifact Registry | por GB, con limpieza automática a 30 días |
| **Cloud SQL producción** | **permanente** |
| **Cloud SQL staging** | **solo en horario laboral** |

La base de staging se apaga a las 21:00 y se enciende a las 07:00 de lunes a
viernes, hora de Monterrey. Fuera de ese horario staging responde con error de
conexión: **no es un fallo**. Para encenderla antes, ejecutar el trabajo
`narrateca-staging-sql-encender` desde Cloud Scheduler.

## Puesta en marcha

Se hace una vez por ambiente, y necesita `gcloud` autenticado con permisos de
administración sobre el proyecto.

### 1. Habilitar las APIs

```bash
gcloud config set project TU_PROYECTO

gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  servicenetworking.googleapis.com \
  cloudscheduler.googleapis.com \
  iamcredentials.googleapis.com \
  compute.googleapis.com
```

### 2. Crear el bucket del estado de Terraform

El estado guarda contraseñas generadas, así que el bucket no es público y tiene
versionado: un `terraform apply` mal hecho no debe ser irreversible.

```bash
gcloud storage buckets create gs://TU_PROYECTO-terraform \
  --location us-central1 --uniform-bucket-level-access
gcloud storage buckets update gs://TU_PROYECTO-terraform --versioning
```

### 3. Aplicar un ambiente

```bash
cd infra/envs/staging   # o envs/prod

terraform init -backend-config="bucket=TU_PROYECTO-terraform"

terraform apply \
  -var project_id=TU_PROYECTO \
  -var project_number=EL_NUMERO_DEL_PROYECTO \
  -var github_repository=organizacion/repositorio
```

El número del proyecto se obtiene con:

```bash
gcloud projects describe TU_PROYECTO --format="value(projectNumber)"
```

La primera aplicación despliega una imagen de ejemplo en Cloud Run. El primer
despliegue real la sustituye.

### 4. Configurar GitHub

Terraform imprime los valores. Se cargan como **variables** del ambiente
correspondiente en GitHub (Settings → Environments → staging / production).
No son secretos: ninguno sirve sin el token que GitHub emite en cada ejecución.

```bash
terraform output
```

| Variable en GitHub | De dónde sale |
|---|---|
| `WIF_PROVIDER` | `workload_identity_provider` |
| `DEPLOY_SERVICE_ACCOUNT` | `deployer_service_account` |
| `RUNTIME_SERVICE_ACCOUNT` | cuenta `narrateca-<entorno>-run@…` |
| `REGISTRY_URL` | `registry_url` |
| `API_URL` | `backend_url` |
| `WEB_URL` | `frontend_url` |
| `MEDIA_URL` | `https://storage.googleapis.com/narrateca-<entorno>-publico` |

Para producción conviene además marcar el ambiente `production` con revisores
obligatorios: así un despliegue espera aprobación de una persona.

### 5. Crear la primera cuenta de administración

```bash
gcloud run jobs deploy narrateca-admin-inicial \
  --image REGISTRY_URL/api:prod --region us-central1 \
  --service-account narrateca-prod-run@TU_PROYECTO.iam.gserviceaccount.com \
  --network narrateca-prod --subnet narrateca-prod \
  --vpc-egress private-ranges-only \
  --set-secrets DATABASE_URL=narrateca-prod-database-url:latest \
  --command python \
  --args -m,app.cli,crear-admin,--email,admin@tec.mx,--nombre,Administración,--password,LA_CONTRASEÑA

gcloud run jobs execute narrateca-admin-inicial --region us-central1 --wait
```

Después de ejecutarlo, **borrar el trabajo**: su definición conserva la
contraseña en la configuración del servicio.

```bash
gcloud run jobs delete narrateca-admin-inicial --region us-central1 --quiet
```

### 6. Cargar la credencial del proveedor de modelo de lenguaje

Terraform crea el secreto vacío a propósito, para que la credencial no quede en
el estado.

```bash
echo -n "LA_CREDENCIAL" | \
  gcloud secrets versions add narrateca-prod-llm-api-key --data-file=-
```

## Seguridad

**Sin llaves de cuenta de servicio.** GitHub se autentica con Workload Identity
Federation: presenta un token firmado por su propio emisor y GCP devuelve
credenciales de vida corta. La alternativa —una llave JSON como secreto del
repositorio— es una credencial de larga vida que, si se filtra, entrega el
proyecto entero y no caduca sola.

La condición de atributo del proveedor limita quién puede pedir esas
credenciales al repositorio declarado. Sin ella, cualquier repositorio de GitHub
podría hacerlo.

**La base de datos no tiene IP pública.** Solo se alcanza desde la red privada,
mediante salida directa a VPC desde Cloud Run. No se usa conector serverless
porque mantendría instancias encendidas de forma permanente.

**Dos buckets, no dos carpetas.** El material sensible vive en un bucket con
`public_access_prevention` forzado, que nunca tuvo acceso público que revocar.

## Orden de un despliegue

```
   copia de seguridad (solo producción)
            ↓
   migraciones de base de datos
            ↓
   despliegue del backend
            ↓
   despliegue del frontend
            ↓
   verificación de que responde
            ↓
   auditoría de consentimiento del índice
            ↓
   si algo falló → reversión del tráfico
```

Las migraciones van **antes** del código nuevo. Al revés, el código nuevo
encontraría un esquema viejo y fallaría en cada petición durante la ventana
intermedia.

La reversión redirige el tráfico a la revisión anterior, que Cloud Run conserva.
No vuelve a desplegar nada, así que es cuestión de segundos.

## La campaña de transcripción

El módulo de GPU **no forma parte del `apply` normal**. Se crea para transcribir
el archivo, se ejecuta el trabajo por lotes y se destruye. Que aparezca en el
estado de Terraform después de terminar la campaña es un defecto, no una
configuración: una VM con GPU encendida consume créditos del orden de cientos de
dólares al mes.

Ese módulo se escribe cuando llegue la campaña (tarea 1.10).
