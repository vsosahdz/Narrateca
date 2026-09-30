# Estructura del backend

## Módulos por dominio, no por capa

```
app/
├── main.py                punto de entrada, middleware, traducción de errores
├── api/v1.py              agregación de routers
├── core/                  infraestructura transversal
│   ├── config.py          variables de entorno
│   ├── database.py        motor, sesión, Base declarativa
│   ├── errors.py          errores de dominio (sin HTTP)
│   ├── openapi.py         metadatos de Swagger
│   └── security.py        hashing de contraseñas
└── modules/
    ├── themes/            ← módulo plantilla, copiar esta forma
    │   ├── models.py      SQLAlchemy: tablas
    │   ├── schemas.py     Pydantic: entrada y salida
    │   ├── repository.py  acceso a datos, sin reglas
    │   ├── service.py     reglas de negocio, sin HTTP
    │   └── router.py      HTTP, validación, códigos de estado
    ├── content/
    ├── news/
    ├── team/
    ├── admin/
    ├── ingest/
    └── chat/
```

Los módulos se agrupan **por dominio**. Agruparlos por capa (`routers/`,
`services/`, `models/` en la raíz) es lo que más se ve en tutoriales y lo que
peor escala: para tocar una funcionalidad hay que saltar entre cuatro carpetas
lejanas.

## Equivalencia con MVC

FastAPI no es MVC de forma nativa. La equivalencia adoptada:

| MVC clásico | Capa en el proyecto | Responsabilidad |
|---|---|---|
| Controller | `router.py` | HTTP, validación de entrada, autorización, códigos de estado |
| Model | `models.py` + `repository.py` | Tablas y acceso a datos |
| Model (negocio) | `service.py` | Reglas de negocio |
| View | `schemas.py` | Representación JSON de entrada y salida |

## Reglas de las capas

```
   router  ──▶  service  ──▶  repository  ──▶  models
     │            │              │
   conoce      no conoce      no conoce
   HTTP          HTTP        reglas de negocio
```

1. **El router no contiene reglas de negocio.** Si aparece un `if` que decide
   algo del dominio, pertenece al servicio.
2. **El servicio no conoce HTTP.** No importa `fastapi`, no devuelve
   `JSONResponse`, no conoce códigos de estado. Lanza errores de
   `app.core.errors`; el router los traduce.
3. **El repositorio no contiene reglas.** Solo lee y escribe. Si aparece una
   validación, pertenece al servicio.
4. **Los esquemas no acceden a la base de datos.** Son estructuras de datos.

Esta separación es la que permite probar las reglas de negocio sin levantar un
servidor HTTP, y la que hace que cambiar de proveedor de modelo de lenguaje sea
una variable de entorno (ver `design.md`, decisión 3).

## Crear un módulo nuevo

```bash
cp -r app/modules/themes app/modules/<dominio>
```

Después:

1. Renombrar el modelo y su `__tablename__`.
2. Ajustar esquemas, repositorio y servicio.
3. Cambiar el `prefix` y el `tags` del router.
4. Registrar el router en `app/api/v1.py`.
5. Agregar la etiqueta correspondiente en `app/core/openapi.py`.
6. Generar la migración: `alembic revision --autogenerate -m "<descripción>"`.

## Errores de dominio

Los servicios lanzan errores de `app.core.errors`; `main.py` los traduce:

| Error | HTTP |
|---|---|
| `NotFoundError` | 404 |
| `ConflictError` | 409 |
| `ValidationError` | 422 |
| `PermissionDeniedError` | 403 |
| `ConsentViolationError` | 422 |

`ConsentViolationError` existe por separado a propósito: las violaciones de
consentimiento son la razón de ser de buena parte del diseño y deben poder
auditarse aparte de una validación ordinaria.
