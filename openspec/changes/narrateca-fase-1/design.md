## Context

NarraTECa parte de cero en código, pero **no** parte de cero en contenido: existe un
archivo testimonial del equipo de investigación, heterogéneo y sin estructura común,
parcialmente transcrito. Eso invierte el orden habitual de un proyecto web: el primer
trabajo real no es el gestor de contenidos sino el inventario y la importación.

Tres restricciones dan forma a todo el diseño:

1. **Confidencialidad.** El material está sujeto a un acuerdo que limita quién puede
   utilizarlo. Minimizar lo que sale hacia terceros es un requisito, no una preferencia.
2. **Un semestre con equipo de 2 a 4 personas.** El alcance ya fue recortado de manera
   deliberada (ver No-Goals) y el diseño debe evitar trabajo que no sea imprescindible.
3. **El tema del proyecto obliga a coherencia.** Una plataforma sobre mujeres con
   discapacidad que no es accesible se desacredita sola, y un chatbot construido sobre
   testimonios de sobrevivientes que inventa afirmaciones destruye el valor del archivo
   que pretende difundir.

La arquitectura resultante:

```
  NAVEGADOR                 GCP · Cloud Run              GCP · recursos
  ─────────                 ───────────────              ──────────────

  ┌────────────┐  HTTPS  ┌───────────────────┐       ┌──────────────────┐
  │  Next.js   │◄───────▶│   FastAPI /api/v1 │──────▶│ PostgreSQL       │
  │ App Router │         │   OpenAPI nativo  │       │ + pgvector       │
  │   es / en  │         │                   │       └──────────────────┘
  └────────────┘         │   modules/        │
                         │    ├─ content/    │──────▶┌──────────────────┐
  público:               │    ├─ chat/       │       │ Cloud Storage    │
  home · 4 temas         │    ├─ news/       │       │ media + .vtt     │
  chatbot · equipo       │    ├─ team/       │       └──────────────────┘
                         │    ├─ admin/      │
  admin (con rol):       │    └─ ingest/     │       ┌──────────────────┐
  CMS · panel            └─────────┬─────────┘  ┌───▶│  Ollama Cloud    │
                                   │            │    │  (generación)    │
                                   ▼            │    └──────────────────┘
                         ┌───────────────────┐  │
                         │ e5-small · LOCAL  │  │  solo salen la consulta
                         │ (embeddings, ONNX)│──┘  y 4-6 fragmentos
                         └───────────────────┘

  TRABAJO ÚNICO, FUERA DE LÍNEA:
  ┌────────────────────────────────────────────────────────────┐
  │ VM efímera con GPU → Whisper → transcripciones + subtítulos │
  │ se levanta unos días y se destruye                          │
  └────────────────────────────────────────────────────────────┘
```

## Goals / Non-Goals

**Goals:**

- Convertir un archivo disperso en un catálogo consultable, citable y con procedencia
  verificable.
- Que el chatbot funcione como puerta de entrada al archivo, no como sustituto: cada
  afirmación trazable a una pieza real.
- Que el consentimiento de cada persona testimoniante sea un dato del sistema y no un
  acuerdo verbal: publicar en el sitio y alimentar al chatbot son permisos distintos.
- Que cada comunidad pueda activar su chatbot de forma independiente, sin esperar a
  las otras tres.
- Que el archivo nunca salga completo hacia un tercero.
- Que la fase 2 (voz, avatar, certificación de accesibilidad, mapas completos) no
  requiera rehacer el modelo de datos.

**Non-Goals:**

- Avatar, síntesis de voz y entrada por voz. La política de voz por tema sí se modela
  ahora; no se implementa.
- Certificación WCAG 2.2 AA y videos con Lengua de Señas Mexicana.
- Mapas interactivos completos (rutas, coropléticos, puntos de interés como
  visualizaciones plenas).
- Buscador de texto libre sobre el archivo.
- Traducción del contenido escrito al inglés.
- Agregación automática de noticias por RSS.
- Inicio de sesión institucional del Tec.
- Cualquier funcionalidad de donación.

## Decisions

### 1. El chatbot es una "narradora anclada", no un personaje

Habla con calidez y en primera persona del colectivo ("muchas de nosotras contamos…"),
pero toda afirmación concreta proviene de un fragmento recuperado, citado entre comillas
y enlazado a su pieza original. Nunca inventa biografía, fecha, lugar ni cifra.

**Alternativas descartadas:**

- *Curadora* (solo devuelve citas sin parafrasear): máxima fidelidad, pero se siente un
  buscador y desperdicia la interfaz conversacional.
- *Personaje* (primera persona con libertad narrativa): mucho más inmersivo, pero pone
  palabras en boca de una persona que no existe, usando el testimonio de personas que sí
  existen. Indefendible académicamente y frágil ante cualquier alucinación.

**Por qué importa técnicamente:** el anclaje reduce lo que se le exige al modelo. La
tarea pasa de "sé un personaje convincente" a "cose estos fragmentos con calidez y cita
la fuente", que es una tarea que resuelven bien incluso modelos medianos. La decisión
ética y la decisión de ingeniería apuntan al mismo lado.

### 2. Solo salen fragmentos, nunca el archivo

Los embeddings se generan **localmente** (ver decisión 16 para la elección de modelo) y
la transcripción corre **localmente** con Whisper. Hacia Ollama Cloud viajan únicamente la consulta del usuario
y los 4 a 6 fragmentos recuperados para esa pregunta.

```
   SE QUEDA EN CASA                      SALE HACIA EL TERCERO
   ════════════════                      ═════════════════════
   Archivo completo                      Consulta del usuario
   Transcripciones                       4-6 fragmentos recuperados
   Embeddings de todo el corpus          Respuesta generada (regresa)
   Índice vectorial (pgvector)
   Media y subtítulos
```

**Alternativa descartada:** usar embeddings gestionados por API. Es el error más común
al montar un RAG "privado": se corre el modelo de generación con cuidado y se manda el
corpus entero al proveedor de embeddings. Habría anulado la restricción entera.

**Nota sobre el proveedor de generación:** el equipo eligió Ollama Cloud. Es una
decisión consciente que introduce un tercero en el flujo y requiere contrato de
encargado de tratamiento. Se mitiga con la decisión 3.

### 3. El LLM vive detrás de una interfaz con endpoint configurable

El módulo `chat` define un puerto (`LLMProvider`) con implementaciones intercambiables.
Cambiar de Ollama Cloud a Ollama local sobre GPU dedicada, o a otro proveedor, es una
variable de entorno.

**Por qué:** el uso de Ollama Cloud está pendiente de confirmación legal. Si la respuesta
es negativa, el proyecto no puede quedar bloqueado por una decisión de arquitectura.

**Alternativa descartada:** llamar al proveedor directamente desde el servicio de chat.
Menos código, pero convierte una pregunta legal abierta en una deuda de refactorización.

### 4. Código propio delgado para el RAG, sin LangChain en fase 1

El flujo de fase 1 es: detectar idioma → embeber consulta → buscar en pgvector con filtro
de tema y consentimiento → armar prompt → transmitir respuesta → registrar la interacción.
Son pocas piezas explícitas y depurables.

**Alternativas descartadas:**

- *LangChain*: añade abstracciones y dependencias que aquí no pagan su costo, y dificulta
  responder la pregunta más frecuente del proyecto, que será "¿por qué el modelo dijo esto?".
- *LangGraph*: se justifica cuando el flujo tiene ramas reales. Hoy tiene una (contención
  ante revelación personal). Se adopta cuando el grafo lo amerite, y la interfaz del
  servicio está diseñada para permitirlo sin tocar routers.

### 5. Un solo modelo de contenido compartido por los cuatro temas

`ContentItem` con `type` (foto, testimonio, video, entrevista, noticia, enlace curado,
contenido geográfico) y `theme`. Los cuatro temas son datos, no código.

**Alternativa descartada:** esquema por tema. Habría significado construir el gestor de
contenidos cuatro veces y el importador cuatro veces, con un semestre disponible.
Además, agregar una quinta comunidad sería un refactor en vez de un registro.

### 6. El consentimiento es un campo del esquema, no un documento aparte

Cada pieza lleva:

```
ContentItem
  ├── consent_scope : public | site_only | no_ai
  ├── attribution   : nombre | seudónimo | anónimo
  └── sensitivity   : normal | alta
```

`no_ai` significa que la pieza se publica en el sitio pero **nunca** entra al índice
vectorial. Una persona puede haber autorizado la difusión de su testimonio sin autorizar
que un modelo lo reformule; son permisos distintos y el sistema debe poder representarlos.

**Alternativa descartada:** tratar "publicado" como sinónimo de "indexado". Simplifica el
código y hace imposible honrar un consentimiento parcial.

### 7. El panel de administración es la puerta de entrada del RAG

Publicar contenido modifica lo que la persona sintética puede decir. Ambas cosas viven en
la misma transacción conceptual:

```
        ADMIN PUBLICA UNA PIEZA
                  │
                  ├──────────▶ visible en /es/<tema>
                  │
                  └──────────▶ si consent_scope != no_ai:
                               segmentar → embeber → indexar
                               con review_status = pendiente
```

La ingesta es **automática con revisión posterior**: entra al índice de inmediato y queda
marcada como no revisada en el panel, donde un rol autorizado puede aprobarla o retirarla.

**Alternativas descartadas:**

- *Aprobación previa obligatoria*: más control, pero añade un paso manual por pieza a un
  equipo pequeño que va a importar cientos de ítems.
- *Sin revisión*: ágil, pero cualquier error editorial llega de inmediato a lo que el
  chatbot afirma, sin forma sistemática de detectarlo.

### 8. Activación del chatbot por comunidad, no global

`PersonaConfig` tiene estado y el corpus lo gobierna:

```
   ┌─────────────┐  corpus < umbral   ┌─────────────┐
   │  PRÓXIMA-   │◄───────────────────│  BORRADOR   │
   │   MENTE     │                    │ (solo admin)│
   └──────┬──────┘                    └─────────────┘
          │ corpus ≥ umbral y revisado
          ▼
   ┌─────────────┐
   │   ACTIVA    │  visible y conversable en el selector público
   └─────────────┘
```

El selector público muestra siempre las cuatro comunidades; las no activas aparecen como
"próximamente".

**Por qué:** desacopla el chatbot del inventario del archivo. Si tres comunidades tienen
material listo y una no, salen tres. Convierte el mayor riesgo de calendario del proyecto
en algo gradual en vez de todo-o-nada.

**Alternativa descartada:** lanzar las cuatro personas juntas. Un solo archivo atrasado
habría bloqueado la capacidad más visible del proyecto.

### 9. Recuperación cross-lingual sobre corpus en español

El chatbot responde en el idioma en que se le escribe, pero el archivo está en español.
bge-m3 es multilingüe, así que una pregunta en inglés recupera fragmentos en español sin
traducir la consulta. Las citas textuales se muestran **en español** con su traducción
adjunta, nunca traducidas en silencio.

**Alternativa descartada:** traducir la consulta antes de recuperar. Añade una llamada al
modelo, latencia y un punto más de pérdida de significado.

**Alternativa descartada:** traducir las citas sin marcarlas. Traducir un testimonio es
una decisión editorial, y presentarlo como si fuera la voz original sería falsearlo.

### 10. Estructura modular por dominio en FastAPI

FastAPI no es MVC de forma nativa. La equivalencia adoptada:

```
   MVC clásico          Capa en el proyecto
   ───────────          ───────────────────
   Controller     →     routers/       HTTP, validación, auth, códigos de estado
   Service        →     services/      lógica de negocio (aquí vive el RAG)
   Model          →     models/ + repositories/
   View           →     schemas/       Pydantic de entrada y salida; la vista es JSON
```

Los módulos se agrupan **por dominio** (`modules/content/`, `modules/chat/`, …), cada uno
con sus cuatro capas adentro.

**Alternativa descartada:** agrupar por capa (`routers/`, `services/`, …) en la raíz. Es
lo que más se ve en tutoriales y lo que peor escala: para tocar una funcionalidad hay que
saltar entre cuatro carpetas lejanas.

### 11. Next.js App Router, no SPA pura

**Por qué:** NarraTECa es un proyecto de divulgación. Un testimonio que no aparece en
buscadores o que al compartirse en mensajería se ve como una tarjeta gris sin título está
fallando en su misión, no en su stack. El renderizado en servidor, el enrutamiento por
idioma y las vistas previas por página son parte del producto.

**Alternativa descartada:** React + Vite. Más simple y más barato de operar, pero cobra
justo lo que este proyecto necesita.

**Consecuencia:** como el backend es Python, en Next **no se usan API routes**. Next queda
como capa de renderizado y ruteo, lo que mantiene limpia la separación front/back.

### 12. Los cimientos de accesibilidad entran en fase 1, la certificación en fase 2

```
   SE POSPONE A FASE 2         ENTRA EN FASE 1
   ═══════════════════         ═══════════════
   Auditoría formal            alt_text obligatorio en el CMS
   Pruebas con lectores        HTML semántico y navegación por teclado
   Certificación WCAG 2.2 AA   Tokens de contraste verificados
   Videos con LSM              Subtítulos es/en
```

**Por qué:** es una diferencia de costo, no de prioridad. Si la fase 1 entra con cientos
de imágenes sin texto alternativo, la fase 2 es una campaña manual de descripciones. Si el
campo es obligatorio desde el primer día, la fase 2 es solo la auditoría. Con los
subtítulos ocurre lo mismo: como el archivo se transcribe de todos modos para el RAG,
salen del mismo trabajo; no hacerlo ahora es pagarlo dos veces.

### 13. Transcripción en instancia efímera con GPU

La campaña de transcripción con Whisper se corre en una VM con GPU que se levanta, procesa
por lotes y se destruye.

**Alternativa descartada:** mantener una VM con GPU encendida permanentemente. Costaría
del orden de cientos de dólares al mes en créditos para un trabajo que es esencialmente
único, ahora que la generación corre en Ollama Cloud.

### 14. Infraestructura declarada con Terraform

Toda la infraestructura de GCP se declara en Terraform, con el estado remoto en un bucket
de Cloud Storage y bloqueo habilitado. Nada se crea a mano desde la consola.

Organización:

```
   infra/
   ├── modules/
   │   ├── network/        VPC, subred, acceso privado a servicios
   │   ├── database/       Cloud SQL PostgreSQL + pgvector
   │   ├── storage/        buckets: material sensible y difusión general
   │   ├── registry/       Artifact Registry
   │   ├── service/        servicio de Cloud Run parametrizable
   │   └── transcription/  VM efímera con GPU — NO forma parte del apply normal
   └── envs/
       ├── dev/
       └── prod/
```

**Por qué:** con créditos limitados y un equipo pequeño, la infraestructura creada a mano
es imposible de auditar y de destruir con confianza. Terraform hace que "¿qué está
encendido y cuánto cuesta?" sea una pregunta con respuesta.

**Alternativa descartada:** aprovisionar desde la consola de GCP y documentar los pasos.
Más rápido al inicio, pero la campaña de transcripción exige crear y destruir recursos con
GPU de forma repetida, y hacerlo a mano es exactamente donde se olvidan encendidos.

**Alternativa descartada:** Cloud Deployment Manager o gcloud scripts. Terraform es lo que
el equipo puede leer y revisar en un pull request.

### 15. Sin recursos ociosos: escalado a cero por defecto

Ningún recurso de cómputo permanece encendido sin tráfico.

```
   RECURSO              INACTIVIDAD           DECISIÓN
   ═══════════════════════════════════════════════════════════════
   Cloud Run (API)      escala a 0            min_instances = 0
   Cloud Run (front)    escala a 0            min_instances = 0
   Cloud Storage        sin costo de cómputo  pago por GB almacenado
   Artifact Registry    sin costo de cómputo  política de retención de imágenes
   ───────────────────────────────────────────────────────────────
   VM con GPU           costo altísimo        NO existe en el apply normal;
                                              se crea y se destruye con un
                                              objetivo aparte
   ───────────────────────────────────────────────────────────────
   Cloud SQL            NO escala a cero      único costo permanente;
                                              nivel mínimo en fase 1
```

Dos consecuencias concretas:

1. **La VM con GPU vive en su propio módulo, fuera del `apply` por defecto.** Se crea para
   la campaña de transcripción, se ejecuta el trabajo por lotes y se destruye. Que
   aparezca en el estado de Terraform después de terminar la campaña es un defecto.
2. **Cloud Run usa salida directa a VPC, no conector serverless.** Un conector de VPC
   mantiene instancias encendidas de forma permanente aunque no haya tráfico, lo que
   contradice el objetivo. La salida directa no tiene ese costo base.

**Trade-off aceptado en el arranque en frío:** con `min_instances = 0`, la primera petición
después de un periodo sin tráfico paga el arranque del contenedor. Para un sitio de
divulgación con tráfico intermitente es la elección correcta; si el arranque en frío
resulta molesto en producción, subir a una instancia mínima es un cambio de una línea en
Terraform, y una decisión de costo consciente.

**Cloud SQL es la excepción honesta.** No escala a cero y es la única partida permanente de
la fase 1. Se mitiga con el nivel más pequeño viable y con la certeza de que es un solo
recurso identificable, no una fuga difusa.

### 16. Modelo de embeddings pequeño, ejecutado con ONNX

Se usa `intfloat/multilingual-e5-small` (~470 MB, 384 dimensiones) sobre ONNX Runtime, no
un modelo grande sobre PyTorch.

**Por qué pequeño.** Hay una asimetría que decide la elección:

```
   EMBEBER EL CORPUS            EMBEBER LA CONSULTA
   ═════════════════            ═══════════════════
   por lotes, una vez           en cada pregunta
   puede correr en una VM       el modelo debe estar
   efímera y destruirse         cargado y listo
   → no condiciona nada         → ESTE manda
```

El modelo que atiende consultas debe estar caliente, y con `min_instances = 0` un modelo
de varios gigabytes haría que la primera pregunta tras un periodo sin tráfico esperara a
que se cargue. En un sitio de divulgación con tráfico intermitente, esa es la mayoría de
las primeras preguntas. Medido aquí: e5-small carga en **1,5 s**.

**Por qué ONNX y no PyTorch.** Mismo modelo y mismos vectores; la imagen del contenedor
baja de unos 2,5 GB a unos 400 MB.

**Alternativa descartada:** bge-m3 (~2 GB, 1024 dim). Mejor recuperación, pero exige un
servicio aparte y una instancia siempre encendida, lo que contradice la decisión 15.

**Consecuencia asumida:** el corpus debe reindexarse por completo si algún día se cambia
de modelo. Es un trabajo por lotes, no una migración de datos.

### 17. Recuperación híbrida: el puntaje vectorial absoluto no distingue nada

Los modelos e5 producen similitudes altas por diseño. Medido sobre este corpus:

```
   CONSULTA                          MEJOR PUNTAJE
   ────────                          ─────────────
   «¿cómo fue cruzar la frontera?»       0.807   ← relevante
   «receta de mole poblano»              0.797   ← sin ninguna relación
   «teorema de Pitágoras»                0.788
   «cotización del dólar hoy»            0.784
```

Todo cae entre 0.76 y 0.82, relacionado o no. **Un umbral absoluto sobre la similitud
coseno no puede sostener el requisito de declarar que no hay material**, y sin él el
chatbot respondería a una pregunta sobre mole poblano citando el testimonio de una
migrante: exactamente el fallo que el anclaje pretendía evitar.

La solución adoptada es **búsqueda híbrida**: el índice vectorial se combina con la
búsqueda léxica de PostgreSQL en español, y los dos ordenamientos se fusionan.

```
   consulta
      ├──▶ vector (pgvector)      similitud semántica
      └──▶ léxico  (tsvector es)  coincidencia de palabras
                  │
                  ▼
        fusión de ordenamientos
                  │
                  ▼
     sin coincidencia léxica ni
     ventaja semántica clara
                  │
                  ▼
        «no tengo material sobre eso»
```

«Mole poblano» no comparte ninguna palabra con el corpus: donde el vector no discrimina,
el léxico sí. Y no suma modelos ni peso al arranque en frío, porque usa la búsqueda de
texto completo que PostgreSQL ya ofrece.

**Alternativa descartada:** agregar un reordenador cruzado. Mejor discriminación, pero
suma otro modelo de cientos de megabytes al arranque, justo lo que se evitó en la
decisión 16.

**Alternativa descartada:** dejar la decisión al prompt del modelo de lenguaje. Barato,
pero delega en el proveedor una garantía que la spec exige del sistema, y gasta una
llamada por cada pregunta fuera de tema.

### 18. El umbral se calibra contra un conjunto de evaluación, no a ojo

El umbral de relevancia no puede fijarse por intuición: el descubrimiento de la decisión
17 ocurrió precisamente porque el valor elegido a ojo (0.35) resultó no significar nada.

Se construye un conjunto de preguntas sobre el archivo real, con respuesta esperada y con
preguntas deliberadamente fuera de tema, y el umbral se deriva de ahí. Es trabajo del
equipo de investigación, y es la única forma de saber si el chatbot funciona **antes** de
que lo use alguien de fuera.

**Alternativa descartada:** exponer el umbral en el panel para ajustarlo en caliente.
Alguien terminaría bajándolo para que el chatbot «responda más», rompiendo el anclaje sin
darse cuenta y sin dejar rastro de por qué.

### 19. Segmentación de tamaño fijo con solape, cortando en límite de oración

Fragmentos de unos 800 caracteres con 120 de solape, ajustando el corte a la frontera de
oración más cercana.

**Por qué uniforme.** Hace predecible el tamaño de lo que se recupera y de lo que se envía
al proveedor de lenguaje, que es la superficie expuesta de la decisión 2.

**Por qué en límite de oración.** Sin ese ajuste, una cita puede empezar a media frase, y
en un testimonio eso cambia lo que la persona dijo.

**Alternativa descartada:** segmentar por párrafo natural. Respeta mejor las pausas de
quien narra, pero produce fragmentos de tamaño muy desigual: los muy cortos se recuperan
mal y los muy largos diluyen la señal.

### 20. Un documento que cambia en disco avisa, no sobrescribe

Cuando un documento ya importado cambia en el archivo, el sistema lo marca como
desactualizado y espera una decisión del equipo.

**Por qué.** Reimportar automáticamente descartaría en silencio cualquier corrección
editorial hecha en el panel, y las transcripciones se corrigen a mano precisamente porque
la extracción automática se equivoca con nombres propios y términos locales.

**Alternativa descartada:** sobrescribir siempre. Ágil, y destruye trabajo humano sin
avisar.

### 21. Video mixto según sensibilidad

Testimonios sensibles en Cloud Storage con reproductor propio; contenido de difusión
general puede ir en YouTube. El `ContentItem` distingue ambos casos.

**Por qué:** un testimonio de una sobreviviente rodeado de anuncios y de un carrusel de
recomendaciones algorítmicas es un problema de dignidad, no solo de control técnico.

**Alternativa descartada:** todo en YouTube. Más barato y más simple, con streaming ya
resuelto, pero inaceptable para el material sensible.

## Risks / Trade-offs

**[El uso de Ollama Cloud puede ser incompatible con el acuerdo de confidencialidad]**
→ Es el único riesgo capaz de obligar a rediseñar. Mitigación: la decisión 3 deja el
proveedor detrás de una interfaz configurable, de modo que migrar a Ollama local sea un
cambio de configuración. La confirmación legal se trata como tarea bloqueante temprana,
no como trámite tardío.

**[El inventario del archivo desordenado siempre se subestima]**
→ Es la tarea con mayor varianza del proyecto. Mitigación: la decisión 8 desacopla la
activación del chatbot del avance del inventario, y el sitio público puede lanzarse con el
contenido que exista. Se recomienda cerrar el inventario de una sola comunidad completa
antes de generalizar el importador.

**[Un semestre con 2-4 personas es ajustado para el alcance completo]**
→ El recorte ya se hizo de forma deliberada (mapas completos y buscador fuera). Mitigación
adicional: el modelo de contenido geográfico se define ahora aunque su visualización sea
mínima, para que la fase 2 no toque el esquema.

**[El chatbot puede citar contenido retirado o desactualizado]**
→ Publicar, despublicar e indexar deben mantenerse consistentes. Mitigación: retirar o
despublicar una pieza elimina sus fragmentos del índice en la misma operación, y el panel
de control expone la cobertura del índice (publicadas vs. indexadas vs. excluidas) para
que la divergencia sea visible.

**[Alguien va a contarle su propia historia de violencia al chatbot]**
→ No es un caso borde, es un caso central. La decisión de producto es un mensaje de
contención sin catálogo de recursos. Trade-off aceptado: es más simple de implementar,
pero deja a esa persona sin una vía concreta de ayuda. Conviene revisarlo con el equipo de
investigación antes del lanzamiento y tenerlo como candidato temprano de fase 2.

**[Guardar conversaciones acumula revelaciones personales]**
→ Retención larga y anónima fue la decisión. Mitigación: no se almacena IP ni identificador
de usuario, el aviso de privacidad aparece antes del primer mensaje, y el registro incluye
los fragmentos recuperados porque su valor es evaluar el RAG, no perfilar personas.

**[Georreferenciar testimonios puede identificar a una persona]**
→ Un punto exacto en una comunidad pequeña puede exponer a una sobreviviente. Mitigación:
`geo-content` obliga a agregación a nivel municipio o entidad cuando el dato provenga de un
testimonio marcado como sensible; el punto exacto queda reservado a organizaciones,
servicios y espacios públicos.

**[Next.js añade operación que un SPA no requiere]**
→ Hay que mantener un contenedor con Node en Cloud Run en vez de servir archivos estáticos.
Trade-off aceptado conscientemente a cambio de indexación y vistas previas.

## Migration Plan

No hay migración de sistema previo; hay **importación de archivo**.

1. **Confirmación legal del uso de Ollama Cloud.** Bloqueante para la capacidad de chat,
   no para el resto.
2. **Inventario de una comunidad piloto.** Catalogar el material de un solo tema para
   descubrir la forma real de los datos antes de generalizar el importador.
3. **Esquema y CMS.** `content-catalog` y `admin-cms` primero: sin ellos no hay dónde
   aterrizar lo importado.
4. **Campaña de transcripción.** VM efímera con GPU, Whisper por lotes sobre el material
   audiovisual. Produce texto para el RAG y subtítulos en ambos idiomas.
5. **Importación masiva** al esquema, con `consent_scope` explícito por pieza.
6. **Sitio público** con el contenido ya cargado.
7. **Ingesta al RAG y chatbot** activando primero la comunidad con corpus más completo.
8. **Panel de control** al final, cuando ya existan datos que valga la pena mirar.

**Estrategia de reversión:** cada comunidad puede volver a estado "próximamente" sin
afectar a las demás, y el índice vectorial es reconstruible desde PostgreSQL, que es la
fuente de verdad. Ninguna operación del chatbot modifica el archivo.

## Open Questions

1. **¿El área legal confirma por escrito el uso de Ollama Cloud, con contrato de encargado
   de tratamiento?** Es la única pregunta capaz de cambiar la arquitectura.
2. **¿Qué comunidad tiene el archivo más completo?** Define el orden de activación del
   chatbot y qué tema se usa como piloto del importador.
3. **¿Cuál es el umbral de corpus para que una persona pase a estado activa?** Debe
   definirse con el equipo de investigación, no por criterio técnico.
4. **¿Qué dice exactamente el aviso previo al primer mensaje del chat?** Requiere redacción
   del equipo: qué es, qué no es, y que las conversaciones se guardan de forma anónima.
5. **¿Qué muestra el mapa de cada tema y de dónde salen sus datos?** Necesario antes de
   fase 2; en fase 1 solo condiciona el modelo, no la visualización.
6. **¿El mensaje de contención es suficiente, o el equipo prefiere agregar recursos de
   ayuda?** Decisión de producto revisable antes del lanzamiento.
