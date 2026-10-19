> **Convenciones de marcado**
> - 🔒 **Bloqueante**: otras tareas dependen de esta; hacerla temprano.
> - 📦 **Depende del inventario**: no puede completarse hasta que el inventario del
>   archivo (grupo 3) haya avanzado lo suficiente.
> - ⚖️ **Depende de confirmación externa**: requiere una decisión del área legal o del
>   equipo de investigación.

## 1. Cimientos del proyecto

- [x] 1.1 🔒 Inicializar el repositorio con la estructura `backend/` y `frontend/`, y definir el flujo de trabajo de ramas y commits
- [x] 1.2 🔒 Crear el proyecto FastAPI con estructura modular por dominio (`modules/<dominio>/{router,service,repository,schemas,models}.py`) y un módulo de ejemplo que sirva de plantilla
- [x] 1.3 Configurar la documentación OpenAPI/Swagger con títulos, descripciones y agrupación por dominio
- [x] 1.4 🔒 Crear el proyecto Next.js con App Router y TypeScript, y establecer la convención de que no se usan API routes
- [x] 1.5 🔒 Aprovisionar PostgreSQL con la extensión pgvector habilitada y configurar el sistema de migraciones
- [x] 1.6 🔒 Crear el esqueleto de Terraform con estado remoto en Cloud Storage, bloqueo habilitado y separación de entornos `dev` y `prod`
- [x] 1.7 Declarar en Terraform los buckets de media con separación entre material sensible y de difusión general, acceso uniforme y sin exposición pública del bucket sensible
- [x] 1.8 Declarar en Terraform la red, Cloud SQL con pgvector y el acceso privado desde Cloud Run mediante salida directa a VPC, sin conector serverless
- [x] 1.9 Declarar en Terraform los servicios de Cloud Run para backend y frontend con `min_instances = 0`, y el Artifact Registry con política de retención de imágenes
- [ ] 1.10 Declarar el módulo de transcripción con GPU como objetivo independiente, fuera del `apply` por defecto, con procedimiento explícito de creación y destrucción
- [x] 1.11 Configurar Secret Manager y la gestión de variables de entorno y secretos para ambos servicios, sin secretos en el código
- [x] 1.12 Definir cuentas de servicio con privilegio mínimo para cada componente
- [x] 1.13 Escribir los Dockerfile de backend y frontend, optimizados para arranque en frío
- [x] 1.14 Definir la canalización de integración y despliegue que construye imágenes, ejecuta pruebas y aplica Terraform
- [x] 1.15 Configurar el arnés de pruebas local de ambos proyectos (el enganche a integración continua va en 1.14)
- [ ] 1.16 Documentar el inventario de recursos con su costo en reposo, y verificar que ningún recurso de cómputo queda encendido sin tráfico

## 2. Sistema de diseño y accesibilidad base

*Prerrequisito de todo el trabajo de interfaz (grupos 6, 7, 9, 11).*

- [x] 2.1 🔒 Definir la capa base de tokens: tipografía, espaciado, radios, superficies y colores de texto
- [x] 2.2 🔒 Definir la capa de acento por tema para las cuatro comunidades
- [x] 2.3 Implementar la verificación automatizada de contraste sobre todas las combinaciones de tokens, e integrarla a la canalización de pruebas
- [x] 2.4 Establecer la regla de lint que impide colores literales en componentes
- [x] 2.5 🔒 Construir los componentes base accesibles (encabezados, botones, enlaces, campos, indicador de foco visible) con marcado semántico y navegación completa por teclado
- [x] 2.6 Implementar el enrutamiento por idioma es/en con español por defecto y el mecanismo de cambio que preserva la página actual
- [x] 2.7 Implementar la declaración de idioma en el marcado, incluyendo bloques de contenido en idioma distinto al de la página

## 3. Inventario del archivo existente

*🔒 Determina el calendario de los grupos 5, 10 y 12. Empezar de inmediato y en paralelo al grupo 1.*

- [ ] 3.1 🔒 ⚖️ Confirmar con el área legal si el uso de Ollama Cloud es compatible con el acuerdo de confidencialidad, y obtener contrato de encargado de tratamiento
- [ ] 3.2 🔒 Ejecutar el inventario manual de una comunidad piloto para descubrir la forma real de los datos antes de generalizar
- [x] 3.3 Construir el proceso automatizado de inventario que recorre el archivo, clasifica por tipo de medio y registra procedencia sin modificar el material original
- [x] 3.8 Definir la convención de carpetas: raíz común con una subcarpeta por comunidad y una por tipo de contenido, y el comando que la crea
- [x] 3.9 Implementar el registro de documentos ya ingeridos, con detección de altas, modificaciones y ausencias entre escaneos
- [ ] 3.4 Ejecutar el inventario sobre las cuatro comunidades y producir el catálogo de elementos, incluyendo los no clasificados
- [ ] 3.5 ⚖️ Determinar con el equipo de investigación el `consent_scope` aplicable por lote o por pieza
- [ ] 3.6 ⚖️ Determinar con el equipo de investigación el umbral de corpus que habilita la activación de una persona
- [ ] 3.7 📦 Elaborar el reporte de inventario por comunidad para definir el orden de activación del chatbot

## 4. Catálogo de contenido

*Prerrequisito de los grupos 5, 6, 7, 8, 9, 10 y 12.*

- [x] 4.1 🔒 Modelar la entidad `ContentItem` con `type`, `theme`, estado de publicación, atribución, sensibilidad y procedencia
- [x] 4.2 🔒 Modelar `theme` como dato almacenado, no como valor codificado, para permitir el alta de una comunidad nueva sin cambios de código
- [x] 4.3 🔒 Implementar el campo `consent_scope` con valor por defecto `no_ai` en creación e importación
- [x] 4.4 Implementar la validación de `alt_text` obligatorio para publicar contenido visual, permitiendo guardar borradores incompletos
- [x] 4.5 Implementar el ocultamiento del nombre real en piezas con atribución anónima o con seudónimo, verificado en la API pública
- [x] 4.6 Implementar las transiciones de estado de publicación (`draft`, `published`, `withdrawn`) y su efecto sobre la visibilidad pública
- [x] 4.7 Implementar los endpoints públicos de listado y detalle de contenido, filtrados por tema, tipo y estado publicado
- [x] 4.8 Escribir las pruebas de los escenarios de `content-catalog`, con énfasis en los de consentimiento y atribución

## 5. Transcripción e importación

*📦 Depende del inventario (grupo 3) y del catálogo (grupo 4).*

- [ ] 5.1 Aplicar el módulo de transcripción con GPU, ejecutar la campaña y destruirlo al terminar, verificando que no queda ningún recurso con GPU en el estado de Terraform
- [ ] 5.2 🔒 Construir el proceso de transcripción por lotes con Whisper local que produzca, en una sola pasada, el texto para indexación y las pistas de subtítulos en español e inglés
- [ ] 5.3 Implementar la detección de material ya transcrito en el archivo original, para conservarlo y generar solo las pistas faltantes
- [ ] 5.4 📦 Ejecutar la campaña de transcripción sobre el material audiovisual de las cuatro comunidades
- [ ] 5.5 Verificar que ningún fragmento de audio, video o texto se transmite a servicios externos durante la transcripción
- [x] 5.6 📦 Construir el proceso de importación que normaliza las entradas del inventario a `ContentItem`, preservando procedencia
- [x] 5.7 Implementar la idempotencia de la importación y el manejo de fallos por elemento sin interrumpir el lote
- [x] 5.8 Implementar el reporte de importación con conteos por tema y por tipo, y detalle de fallos
- [ ] 5.9 📦 Ejecutar la importación de la comunidad piloto y ajustar el proceso con los hallazgos
- [ ] 5.10 📦 Ejecutar la importación del resto de las comunidades
- [x] 5.11 Escribir las pruebas de los escenarios de `archive-import`

## 6. Panel de administración

*Prerrequisito del grupo 7 y de la operación de los grupos 5, 8 y 9.*

- [x] 6.1 🔒 Implementar el modelo de cuentas con hash de contraseña mediante algoritmo de derivación de clave resistente a fuerza bruta
- [x] 6.2 🔒 Implementar la autenticación por sesión y la protección de toda la sección de administración
- [x] 6.3 🔒 Implementar los roles `admin` y `editor`, con asignación de temas al rol editor
- [x] 6.4 Implementar la autorización por tema en todas las operaciones de contenido, verificando que un editor no pueda operar fuera de sus temas asignados
- [x] 6.5 Implementar la interfaz de creación, edición, publicación, retiro y eliminación de contenido de todos los tipos
- [x] 6.6 Implementar la carga de archivos de media con enrutamiento al almacenamiento correspondiente según sensibilidad
- [x] 6.7 Implementar la gestión y visualización del `consent_scope` en el listado y en el detalle de cada pieza
- [x] 6.8 Implementar la edición de pistas de subtítulos generadas automáticamente
- [x] 6.9 Implementar el registro de auditoría de acciones administrativas con cuenta y marca de tiempo
- [x] 6.10 Escribir las pruebas de los escenarios de `admin-cms`, con énfasis en los de autorización por tema y almacenamiento de contraseñas

## 7. Sitio público

*Depende de los grupos 2, 4 y 6.*

- [x] 7.1 Implementar la página de inicio con los cuatro temas y verificar la ausencia total de elementos de donación en el sitio
- [x] 7.2 Implementar la página temática independiente con agrupación por tipo de contenido y omisión de secciones vacías
- [x] 7.3 Implementar el filtrado por tipo de contenido dentro de cada tema
- [x] 7.4 Implementar la página de detalle de pieza con dirección estable y manejo correcto de piezas retiradas
- [x] 7.5 Implementar la página del equipo de investigación con fotografía, nombre y biografía por integrante, y marcador neutro cuando falte la fotografía
- [x] 7.6 Implementar el reproductor propio para video de sensibilidad alta, sin incrustar servicios de terceros
- [x] 7.7 Implementar la integración con servicio externo de video para material de difusión general
- [x] 7.8 Implementar la selección de pista de subtítulos en el reproductor
- [x] 7.9 Verificar navegación completa por teclado con indicador de foco visible en todas las páginas públicas
- [x] 7.10 Escribir las pruebas de los escenarios de `public-site` e `i18n-subtitles`

## 8. Noticias

*Depende de los grupos 4 y 6.*

- [x] 8.1 Implementar la redacción y publicación de notas propias con título, cuerpo, fecha e imagen destacada opcional
- [x] 8.2 Implementar el registro de enlaces curados con título, medio, fecha y resumen propio obligatorio, sin almacenar el cuerpo del artículo externo
- [x] 8.3 Implementar la sección de noticias por tema ordenada de más reciente a más antigua
- [x] 8.4 Implementar la distinción visual entre notas propias y enlaces externos
- [x] 8.5 Escribir las pruebas de los escenarios de `news`

## 9. Contenido geográfico ⏸ EN PAUSA

*Depende de los grupos 2, 4 y 6.*

- [ ] 9.1 🔒 Modelar el tipo `geo_item` con geometrías de punto, ruta y región, dejando el esquema listo para la fase 2
- [ ] 9.2 Implementar la restricción que impide almacenar coordenadas de punto exacto en piezas derivadas de testimonios de sensibilidad alta
- [ ] 9.3 Implementar la administración de contenido geográfico desde el panel
- [ ] 9.4 Implementar la visualización de mapa mínima en la página temática, omitida cuando no hay contenido geográfico
- [ ] 9.5 Implementar la alternativa textual equivalente al mapa, accesible por teclado y lector de pantalla
- [ ] 9.6 Escribir las pruebas de los escenarios de `geo-content`, con énfasis en los de agregación de datos sensibles

## 10. Ingesta al RAG

*📦 Depende del contenido importado (grupo 5) y del catálogo (grupo 4). Prerrequisito del grupo 11.*

- [x] 10.1 🔒 Integrar el modelo de embeddings multilingüe ejecutado en infraestructura propia
- [x] 10.2 Verificar que ningún texto del archivo se transmite a servicios de embeddings externos
- [x] 10.3 🔒 Implementar la segmentación del texto y el almacenamiento de fragmentos en pgvector con partición por tema
- [x] 10.4 Implementar la referencia de cada fragmento a su `ContentItem` de origen y la resolución de su dirección pública
- [x] 10.5 🔒 Implementar la exclusión de piezas con `consent_scope` igual a `no_ai` en todo el proceso de indexación
- [ ] 10.6 Implementar la ingesta automática al publicar, con estado de revisión `pending` en los fragmentos nuevos
- [ ] 10.7 Implementar la aprobación y el retiro de fragmentos desde el panel, sin afectar la publicación de la pieza
- [ ] 10.8 Implementar la sincronización del índice ante edición, retiro, eliminación y cambio de consentimiento
- [x] 10.9 Implementar la reconstrucción completa del índice de un tema desde la base de datos relacional
- [ ] 10.10 Implementar la auditoría del índice que verifica ausencia de fragmentos huérfanos y de contenido excluido
- [ ] 10.11 Escribir las pruebas de los escenarios de `rag-ingestion`, con énfasis en los de consentimiento y sincronización

## 11. Chatbot

*Depende del grupo 10. ⚖️ La elección de proveedor depende de la tarea 3.1.*

- [x] 11.1 🔒 Definir la interfaz del proveedor de modelo de lenguaje con implementación seleccionable y punto de conexión configurable
- [x] 11.2 Implementar el adaptador del proveedor elegido y verificar que cambiar de proveedor no requiere tocar recuperación, citación ni persistencia
- [x] 11.3 🔒 Modelar `PersonaConfig` por tema con prompt de sistema, corpus, política de voz, política de seguridad, idioma y estado de activación
- [x] 11.4 Registrar la política de voz de las cuatro comunidades, con voz femenina exclusiva para los temas de mujeres, aunque la síntesis no se implemente en esta fase
- [x] 11.5 🔒 Implementar los estados de activación `draft`, `coming_soon` y `active`, independientes entre comunidades
- [ ] 11.6 ⏸ Implementar la página del chatbot con selector que muestra las cuatro comunidades y señala las no disponibles *(a la espera del export de Stitch)*
- [x] 11.7 🔒 Implementar la recuperación filtrada por tema y por consentimiento
- [x] 11.8 🔒 Redactar y ajustar el prompt de sistema de la narradora anclada: primera persona del colectivo, sin inventar hechos, sin biografía individual
- [x] 11.9 Implementar la respuesta de ausencia de material cuando la recuperación no devuelve fragmentos suficientemente relevantes
- [x] 11.10 Implementar la citación en línea con fragmento textual y enlace a la pieza de origen, verificando que los enlaces apuntan a piezas publicadas
- [x] 11.11 Implementar la detección de idioma y la respuesta en español o inglés sobre corpus en español
- [x] 11.12 Implementar la presentación de citas en español con traducción identificada cuando la respuesta esté en inglés
- [ ] 11.13 ⚖️ Redactar con el equipo de investigación el mensaje de contención ante revelaciones personales *(el mecanismo está hecho y es configurable por comunidad; falta la redacción aprobada)*
- [x] 11.14 Implementar la detección de revelación personal y la emisión del mensaje de contención, sin consejo clínico, legal ni terapéutico
- [x] 11.15 Implementar la transmisión progresiva de la respuesta desde el backend hasta la interfaz
- [x] 11.16 Verificar que cada solicitud al proveedor contiene únicamente prompt de sistema, historial de la conversación y fragmentos recuperados
- [x] 11.17 Escribir las pruebas de los escenarios de `chat-personas`, con énfasis en anclaje, citación y minimización de datos enviados

## 12. Persistencia de conversaciones

*Depende del grupo 11.*

- [ ] 12.1 ⚖️ Redactar con el equipo de investigación el texto del aviso de privacidad previo al primer mensaje
- [ ] 12.2 Implementar la presentación del aviso antes de que la persona pueda enviar su primer mensaje
- [ ] 12.3 🔒 Implementar el almacenamiento de conversaciones con identificador de sesión efímero, sin dirección IP ni huella de navegador
- [ ] 12.4 Verificar que dos visitas de una misma persona no pueden vincularse entre sí
- [ ] 12.5 Implementar el registro por turno de los fragmentos recuperados y sus puntuaciones de relevancia
- [ ] 12.6 Implementar el marcado de turnos con mensaje de contención, sin categorización adicional de la persona usuaria
- [ ] 12.7 Implementar la restricción de acceso a los registros exclusivamente para cuentas con rol de administrador
- [ ] 12.8 Implementar el periodo de retención configurable y el proceso de eliminación permanente de registros vencidos
- [ ] 12.9 Escribir las pruebas de los escenarios de `chat-transcripts`, con énfasis en anonimato y control de acceso

## 13. Panel de control

*Depende de los grupos 10 y 12. Las tareas marcadas ⏸ esperan al chatbot; el panel ya las declara como pendientes en su respuesta en vez de reportar cero.*

- [x] 13.1 Implementar la vista de salud del archivo con conteos por tema, por tipo y por estado de publicación
- [x] 13.2 Implementar la vista de cobertura del índice con publicadas, indexadas, excluidas por consentimiento y pendientes de revisión
- [ ] 13.3 ⏸ Implementar la vista de estado de activación de cada persona con el tamaño de su corpus
- [ ] 13.4 ⏸ Implementar la vista de volumen de conversaciones por tema y por periodo
- [ ] 13.5 ⏸ Implementar el listado de turnos sin material relevante, para detectar vacíos del archivo
- [ ] 13.6 ⏸ Implementar el listado de fragmentos más recuperados por tema con enlace a su pieza de origen
- [ ] 13.7 ⏸ Implementar el conteo agregado de turnos con mensaje de contención, sin exponer el texto de las personas usuarias
- [x] 13.8 Implementar la restricción de acceso al panel exclusivamente para cuentas con rol de administrador
- [x] 13.9 Escribir las pruebas de los escenarios de `admin-dashboard`

## 14. Cierre de fase

- [ ] 14.1 Ejecutar una revisión de accesibilidad de los cimientos: marcado semántico, navegación por teclado, texto alternativo presente y contraste verificado
- [ ] 14.2 Auditar que ningún dato distinto de la consulta y los fragmentos recuperados sale hacia el proveedor de modelo de lenguaje
- [ ] 14.3 Auditar el índice completo frente al consentimiento registrado en las cuatro comunidades
- [ ] 14.4 Verificar la ausencia de elementos de donación en todo el sitio
- [ ] 14.5 Revisar que la documentación Swagger describe todos los endpoints con sus esquemas de entrada y salida
- [ ] 14.6 Documentar el procedimiento de despliegue, el de reconstrucción del índice y el de reversión de una comunidad a estado `coming_soon`
- [ ] 14.8 Auditar el estado de Terraform para confirmar que no existen recursos de cómputo encendidos sin tráfico ni instancias con GPU remanentes
- [ ] 14.7 ⚖️ Activar las comunidades cuyo corpus haya alcanzado el umbral acordado
