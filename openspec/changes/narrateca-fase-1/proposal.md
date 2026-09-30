## Why

El equipo de investigación posee un archivo testimonial sobre cuatro comunidades
—migrantes, comunidad LGBTQ+, mujeres con discapacidad, y mujeres y violencia de
género— que hoy vive disperso en carpetas, documentos y grabaciones sin
estructura común. Ese material no es consultable por el público, no es citable, y
buena parte del audiovisual ni siquiera está transcrito, por lo que es invisible
para cualquier búsqueda.

NarraTECa convierte ese archivo en una plataforma pública de divulgación y, sobre
la misma base de datos, ofrece un chatbot que permite conversar con la voz de cada
comunidad. La apuesta central es que el chatbot **no sustituya al archivo sino que
sea una puerta de entrada a él**: cada afirmación que hace proviene de un fragmento
real, citado y enlazado a su pieza original.

## What Changes

- Se crea la plataforma completa desde cero: no existe código previo.
- **Inventario e importación del archivo existente**: catalogación del material
  disperso, normalización a un esquema único e importación masiva.
- **Transcripción por lotes** del material audiovisual con Whisper local. Un solo
  trabajo produce tres entregables: texto para el RAG, subtítulos en español para
  accesibilidad y subtítulos en inglés para traducción.
- **Sitio público en español con interfaz bilingüe es/en**: página de inicio con
  los cuatro temas, una página independiente por tema con fotografías, testimonios,
  videos, entrevistas y noticias, y una página del equipo de investigación con
  fotografía y biografía de cada integrante.
- **Panel de administración** con cuentas propias y roles diferenciados
  (administrador general y editor por tema) para crear, editar y publicar contenido.
- **Panel de control** con métricas de salud del archivo y de las conversaciones.
- **Chatbot con LLM+RAG** en página propia con selector de comunidad. Cada tema
  tiene su propia configuración de persona y su propio corpus. Una comunidad se
  activa públicamente solo cuando su corpus alcanza el umbral definido; mientras
  tanto aparece como "próximamente".
- **Trazabilidad obligatoria**: toda respuesta del chatbot cita en línea los
  fragmentos que la sustentan, con enlace a la pieza original del archivo.
- **Control de consentimiento a nivel de pieza**: el campo `consent_scope` permite
  publicar contenido en el sitio sin que alimente al chatbot.
- **Persistencia anónima de conversaciones** con aviso de privacidad previo, para
  evaluación del RAG e investigación sobre qué pregunta el público.
- **Minimización de exposición a terceros**: los embeddings y la transcripción
  corren localmente; hacia el proveedor de LLM solo viajan la consulta del usuario
  y los fragmentos recuperados, nunca el archivo completo.
- **Sistema de tokens de diseño** con base compartida y color de acento por tema,
  intercambiable editando archivos de código.
- El sitio **no incluye** botones ni funcionalidad de donación en ninguna parte.

## Capabilities

### New Capabilities

- `archive-import`: Inventario del archivo existente, transcripción por lotes con
  Whisper local, y proceso de importación que normaliza material heterogéneo al
  esquema de contenido, preservando procedencia y consentimiento.
- `content-catalog`: Modelo de contenido compartido por los cuatro temas
  (`ContentItem` con `type` y `theme`), incluyendo `consent_scope`, atribución,
  texto alternativo obligatorio y estados de publicación.
- `public-site`: Página de inicio con los cuatro temas, páginas temáticas
  independientes, página del equipo de investigación, y navegación bilingüe.
- `news`: Sección de noticias por tema alimentada por notas propias del equipo y
  por enlaces curados a medios externos con resumen propio.
- `admin-cms`: Autenticación con cuentas propias, roles de administrador y editor
  por tema, y operaciones de creación, edición, publicación y retiro de contenido.
- `admin-dashboard`: Panel de control con salud del archivo (contenido por tema y
  tipo, cobertura del índice, piezas excluidas por consentimiento) y actividad del
  chatbot (volumen, preguntas sin respuesta útil, fragmentos más recuperados).
- `rag-ingestion`: Segmentación, generación local de embeddings, indexación en
  pgvector con partición por tema, respeto de `consent_scope`, e ingesta automática
  al publicar con marca de revisión pendiente.
- `chat-personas`: Configuración de persona por comunidad (prompt, corpus, políticas,
  estado de activación), recuperación cross-lingual, generación anclada con citas en
  línea, transmisión de respuesta en tiempo real, y mensaje de contención ante
  revelaciones personales.
- `chat-transcripts`: Persistencia anónima de conversaciones y de los fragmentos
  recuperados, aviso de privacidad previo al primer mensaje, y exposición de la
  información al panel de control.
- `i18n-subtitles`: Interfaz en español e inglés, subtítulos en ambos idiomas para
  todo el material audiovisual, y gestión de las pistas de subtítulos.
- `design-tokens`: Tokens base compartidos más acento por tema, con contraste
  verificable, intercambiables desde código.
- `geo-content`: Modelo de contenido geográfico capaz de representar puntos, rutas
  y regiones, con visualización mínima en fase 1 y agregación obligatoria cuando el
  dato provenga de un testimonio sensible.

### Modified Capabilities

Ninguna. Es la primera propuesta del proyecto y no existen specs previas.

## Impact

**Código nuevo, sin sistema previo que migrar.**

- **Frontend**: aplicación Next.js (App Router) en TypeScript, con enrutamiento por
  idioma, sitio público y sección de administración.
- **Backend**: servicio FastAPI con módulos por dominio (`content`, `chat`, `news`,
  `team`, `admin`, `ingest`), documentación OpenAPI/Swagger generada automáticamente.
- **Datos**: PostgreSQL con extensión pgvector para el índice del RAG; Google Cloud
  Storage para media y pistas de subtítulos.
- **Servicios externos**: Ollama Cloud para generación de texto, detrás de una
  interfaz con endpoint configurable. Es el único punto donde el contenido sale de
  infraestructura propia, y solo en forma de fragmentos recuperados.
- **Procesos fuera de línea**: instancia efímera con GPU para la campaña de
  transcripción con Whisper; se destruye al terminar.
- **Despliegue**: contenedores en Google Cloud Run, base de datos gestionada en GCP.
- **Dependencia externa bloqueante**: confirmación del área legal de que el uso de
  Ollama Cloud es compatible con el acuerdo de confidencialidad, con contrato de
  encargado de tratamiento. Si la respuesta es negativa, la generación debe migrar a
  Ollama local sobre GPU dedicada; la interfaz configurable existe precisamente para
  que ese cambio sea de configuración y no de arquitectura.
- **Dependencia externa de calendario**: el inventario del archivo determina qué
  comunidad puede activar su chatbot primero. Ninguna otra capacidad depende de él.

## No objetivos

Queda explícitamente fuera del alcance de esta fase:

- **Avatar y voz**: síntesis de voz con política por tema (voz femenina exclusiva
  para las iniciativas de mujeres; ambas voces para migrantes y comunidad LGBTQ+),
  entrada por voz, y avatar ilustrado no fotorrealista. La política de voz sí se
  modela en `chat-personas` desde ahora, aunque no se implemente.
- **Certificación WCAG 2.2 AA**: la auditoría formal, las pruebas con lectores de
  pantalla y los videos con Lengua de Señas Mexicana son fase 2. Los cimientos
  (texto alternativo obligatorio, HTML semántico, navegación por teclado, tokens de
  contraste, subtítulos) sí entran en fase 1 porque retrofitearlos es caro.
- **Mapas interactivos completos**: rutas migratorias, coropléticos de incidencia y
  puntos de interés como visualizaciones plenas. En fase 1 solo se modela el tipo de
  contenido geográfico y se entrega la visualización mínima.
- **Buscador de texto libre**: el público navega por tema y filtra por tipo de
  contenido. La búsqueda global se pospone.
- **Traducción del contenido escrito**: testimonios, entrevistas y noticias
  permanecen en español. Solo la interfaz y los subtítulos son bilingües.
- **Agregación automática de noticias**: no hay recolección por RSS ni clasificación
  automática; las noticias se administran manualmente.
- **Catálogo de recursos de ayuda**: ante revelaciones personales el chatbot responde
  con un mensaje de contención, sin derivar a organizaciones ni líneas telefónicas.
- **Inicio de sesión institucional (SSO del Tec)**: la autenticación es con cuentas
  propias; la capa se deja preparada para agregar SSO después.
- **Donaciones**: no se implementan en ninguna fase.
