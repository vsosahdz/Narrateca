# Flujo de trabajo

## Ramas

```
main                    ← siempre desplegable
 └── feat/<capacidad>-<detalle>     nueva funcionalidad
 └── fix/<capacidad>-<detalle>      corrección
 └── chore/<detalle>                infraestructura, dependencias, tooling
 └── docs/<detalle>                 documentación
```

El nombre de `<capacidad>` corresponde a una capacidad de OpenSpec
(`content-catalog`, `chat-personas`, `rag-ingestion`, …), de modo que cada rama
sea rastreable hasta el requisito que implementa.

Ejemplos:

```
feat/content-catalog-consent-scope
feat/chat-personas-citas-en-linea
fix/rag-ingestion-sincronizacion-indice
chore/ci-cobertura
```

Nadie hace commit directo a `main`. Todo entra por pull request con al menos una
revisión.

## Commits

Se usa [Conventional Commits](https://www.conventionalcommits.org/):

```
<tipo>(<ámbito>): <descripción en imperativo>

[cuerpo opcional]

[pie opcional]
```

Tipos: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `perf`, `ci`.

El `<ámbito>` es la capacidad de OpenSpec afectada.

```
feat(content-catalog): agregar consent_scope con valor por defecto no_ai
fix(rag-ingestion): eliminar fragmentos al retirar una pieza publicada
test(chat-personas): cubrir escenarios de citación en línea
```

## Relación con OpenSpec

Cada pull request debe indicar en su descripción qué tareas de
`openspec/changes/<cambio>/tasks.md` completa:

```
Completa: 4.3, 4.4
```

Las casillas de `tasks.md` se marcan en el mismo pull request que implementa la
tarea, no después.

Antes de abrir un pull request:

```bash
openspec validate narrateca-fase-1
```

## Reglas no negociables

Estas se verifican en revisión y, donde es posible, en la canalización de
integración continua:

1. **Nada del material del archivo entra al repositorio.** Ni testimonios, ni
   audio, ni video, ni transcripciones. El `.gitignore` cubre los casos
   conocidos, pero la responsabilidad es de quien hace el commit.
2. **Ningún secreto en el código.** Todo va por variables de entorno.
3. **Ningún color literal en componentes.** Solo tokens (ver `design-tokens`).
4. **Ningún contenido visual sin texto alternativo.** Es requisito de publicación.
5. **Ningún dato del archivo hacia terceros** más allá de los fragmentos
   recuperados por consulta (ver `design.md`, decisión 2).

## Puertos de desarrollo

Este equipo tiene otras aplicaciones en 3000, 3010 y 3100. NarraTECa usa:

```
backend    http://localhost:8000
frontend   http://localhost:3400
Postgres   localhost:5433   (5432 lo ocupa una instalación de Homebrew)
```

Si cambias el puerto del frontend, actualiza `CORS_ORIGINS` en `backend/.env`:
la cookie de sesión no viaja si el origen no está permitido.
