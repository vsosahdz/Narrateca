# Estado del proyecto y cómo continuar

Última revisión: 14 de noviembre de 2026 · commit `4655c57`

Este documento dice **dónde quedó el trabajo y qué sigue**. Para levantar el
entorno está el [README](../README.md); para ramas, commits y puertos,
[flujo de trabajo](flujo-de-trabajo.md); para la arquitectura del backend,
[estructura del backend](estructura-backend.md).

## Dónde está todo

87 de 136 tareas del plan de fase 1 (`openspec/changes/narrateca-fase-1/tasks.md`).

| Grupo | Estado |
|---|---|
| 1. Cimientos | 14/16 — faltan el módulo de GPU efímera (1.10) y el inventario de costos (1.16) |
| 2. Diseño y accesibilidad | completo |
| 3. Inventario del archivo | 3/9 — depende de que haya material real depositado |
| 4. Catálogo de contenido | completo |
| 5. Transcripción e importación | 4/11 — Whisper local, aplazado por decisión de Víctor |
| 6. Panel de administración | completo |
| 7. Sitio público | completo |
| 8. Noticias | completo |
| 9. Contenido geográfico | **en pausa** por decisión de Víctor |
| 10. Ingesta al RAG | 6/11 — faltan revisión/aprobación de fragmentos y la auditoría expuesta |
| 11. Chatbot | 16/17 — solo falta 11.13 |
| 12. Persistencia de conversaciones | sin empezar |
| 13. Panel de control | 4/9 — el resto depende del chatbot |
| 14. Cierre de fase | sin empezar |

La plataforma funciona de punta a punta en local: sitio público en español e
inglés, panel de administración, archivo con detección de documentos nuevos,
índice vectorial y chatbot con citas.

## Lo que está bloqueado, y en quién

Nada de esto lo puede resolver quien escriba código.

**El mensaje de contención (tarea 11.13).** Es lo único que falta del grupo 11.
Cuando alguien le cuenta al chatbot una experiencia propia de violencia o
riesgo, el sistema deja de hacer de narradora y responde con un mensaje breve
que reconoce lo dicho y aclara que es un sistema automatizado. El mecanismo
está hecho y es configurable por comunidad desde la base de datos; **el texto
que hay ahora es un marcador de posición**, señalado con ⚠️ en
`backend/app/modules/chat/safety.py`. Lo redacta el equipo de investigación,
porque es lo que leerá alguien que acaba de contar algo grave.

**Abrir las narradoras.** Tres de las cuatro están en `draft`: solo cuentas de
administración pueden conversar con ellas. Abrirlas es una decisión sobre si
el material de esa comunidad está revisado, no sobre si el código está listo.
Se cambia el campo `activation` de `persona_configs` a `active`.

**El diseño de la página del chatbot.** Lo que hay es sobrio a propósito,
esperando el export de Stitch que Víctor va a pasar. Las carpetas están
creadas en `docs/diseno/`.

**La infraestructura en GCP.** Terraform está escrito y validado, y el
despliegue a staging falla únicamente porque faltan siete variables del
repositorio y aplicar Terraform. Los pasos están en
[`infra/README.md`](../infra/README.md). También quedan por configurar la
protección de rama en `main` y el entorno `production` con revisores.

## Decisiones recientes que no se leen en el código

Las 21 decisiones de arquitectura están en
`openspec/changes/narrateca-fase-1/design.md`. Estas son posteriores y vale la
pena tenerlas presentes antes de tocar el módulo `chat`.

**La recepción no usa modelo de lenguaje.** Es la quinta voz de la página del
chatbot y la única que no es una voz: consulta el índice de cada comunidad
abierta y devuelve una lista de cuáles tienen material. No redacta, así que no
puede inventar ni hablar en primera persona. Una recepción conversacional
habría sido un quinto prompt que calibrar y vigilar, con más riesgo que las
narradoras porque hablaría *sobre* las cuatro comunidades en lugar de desde
una. Si se decide hacerla conversacional, es un cambio consciente, no una
mejora incremental.

**Las citas van como marcadores numerados en el texto.** Eso descansa en que el
modelo los coloque bien, así que hay red en los dos lados: el servidor descarta
los marcadores que no corresponden a un fragmento entregado —conservando la
frase— y la interfaz solo convierte en enlace los que tienen cita detrás,
porque durante la transmisión el texto aún no ha pasado por el servidor.

**Cambiar de comunidad empieza conversación nueva.** El historial de una
comunidad no viaja al prompt de otra. Al implementar el grupo 12 (persistencia)
hay que mantener esa separación: una conversación pertenece a una comunidad.

**Los slugs llevan guion medio, y el identificador no cambió.** El id de cada
tema se deriva con `uuid5` del slug original, así que renombrar regenerando lo
habría cambiado y dejado huérfano el contenido. La migración de siembra sigue
usando la grafía antigua como clave de identidad y otra posterior renombra solo
la etiqueta. **Si algún día se renombra otro slug: hay que migrar también las
tablas que lo guardan como texto** —`chunks`, `archive_documents`,
`persona_configs`—. Pasó una vez y el chatbot dejó de encontrar su corpus sin
que ninguna prueba lo detectara.

## Trampas conocidas del entorno

Todas costaron tiempo al menos una vez.

- **Las reglas amplias de `.gitignore`** (`archive/`, `media/`, `var/`) existen
  para que el material del archivo nunca se versione, y se tragaron dos módulos
  de código sin que nada avisara. Antes de dar por hecho que un archivo nuevo
  está en el repositorio, pasar `scripts/verificar-integridad-repo.sh`. Lo
  ejecuta también la integración continua.
- **Postgres va en el 5433**, porque el 5432 lo ocupa una instalación de
  Homebrew. Si las conexiones fallan con «role does not exist», es que están
  llegando al servidor equivocado.
- **El frontend va en el 3400**; 3000, 3010 y 3100 los ocupan otros proyectos
  de este equipo.
- **Ruff está fijado a una versión exacta.** Un rango abierto hacía que la
  integración continua instalara otra y diera un veredicto distinto al local.
- **`drop_table` no borra los tipos enumerados.** Toda migración que cree un
  enum debe borrarlo en su reversión, o la siguiente aplicación falla con
  `type ... already exists`.

## Lo natural que sigue

**Grupo 12, persistencia de conversaciones.** Es lo que Víctor pidió desde el
encargo original —«guardar las interacciones con el chatbot»— y el grupo 11 ya
dejó el terreno: cada turno tiene su identificador de conversación y el
servicio sabe exactamente qué se envió al proveedor. Nueve tareas.

Después, el resto del grupo 10 (revisión y aprobación de fragmentos desde el
panel, auditoría del índice expuesta) y con ello se cierran las tareas 13.3 a
13.7 del panel de control, que dependían del chatbot.

El grupo 5 (transcripción con Whisper) y el grupo 9 (contenido geográfico)
siguen aplazados por decisión de Víctor.

## Cómo comprobar que todo sigue en pie

```bash
docker start narrateca-db                  # o `docker compose up -d`
cd backend && .venv/bin/python -m pytest -q # 273 pruebas
cd .. && bash scripts/verificar-integridad-repo.sh
```

El estado al cerrar esta sesión: rama `main` al día con el remoto, integración
continua en verde en los cinco trabajos, migraciones aplicadas hasta
`56aa6dfe48d5`, 273 pruebas pasando.
