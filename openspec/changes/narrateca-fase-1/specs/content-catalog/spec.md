## ADDED Requirements

### Requirement: Modelo de contenido compartido entre los cuatro temas

El sistema DEBE (MUST) representar todo el contenido de las cuatro comunidades con una sola
entidad `ContentItem`, discriminada por los campos `type` y `theme`. Los temas DEBEN ser
datos almacenados y no valores codificados en la aplicación.

Los valores de `type` DEBEN incluir al menos: `photo`, `testimony`, `video`, `interview`,
`news_post`, `curated_link` y `geo_item`.

Los valores de `theme` DEBEN incluir al menos: `migrantes`, `lgbtq`,
`mujeres-discapacidad` y `mujeres-violencia`.

#### Scenario: Alta de contenido en cualquier tema

- **WHEN** un editor crea una pieza de contenido de cualquier tipo para cualquiera de los
  cuatro temas
- **THEN** el sistema la almacena como un `ContentItem` con su `type` y `theme`
  correspondientes, sin requerir tablas ni endpoints específicos por tema

#### Scenario: Alta de una quinta comunidad

- **WHEN** un administrador registra un tema nuevo que no existía
- **THEN** el sistema permite crear contenido asociado a ese tema sin cambios de código ni
  migraciones de esquema

#### Scenario: Tipo de contenido no soportado

- **WHEN** se intenta crear un `ContentItem` con un `type` fuera de los valores permitidos
- **THEN** el sistema rechaza la operación con un error de validación que indica los
  valores admitidos

### Requirement: Alcance de consentimiento por pieza

Cada `ContentItem` DEBE (MUST) tener un campo `consent_scope` con exactamente uno de estos
valores: `public`, `site_only` o `no_ai`.

El sistema DEBE tratar la publicación en el sitio y la incorporación al índice del chatbot
como permisos distintos. Una pieza con `consent_scope` igual a `no_ai` DEBE poder
publicarse en el sitio público y NO DEBE entrar nunca al índice vectorial.

El valor por defecto al crear o importar una pieza DEBE ser `no_ai`, de modo que la
incorporación al chatbot sea siempre una decisión explícita.

#### Scenario: Pieza publicable pero excluida del chatbot

- **WHEN** un editor publica un testimonio con `consent_scope` igual a `no_ai`
- **THEN** el testimonio aparece en su página temática pública
- **AND** el sistema no genera ni almacena fragmentos indexables para esa pieza

#### Scenario: Valor por defecto conservador

- **WHEN** se crea o importa un `ContentItem` sin especificar `consent_scope`
- **THEN** el sistema asigna `no_ai`

#### Scenario: Cambio de consentimiento a no_ai sobre pieza ya indexada

- **WHEN** un editor cambia el `consent_scope` de una pieza indexada a `no_ai`
- **THEN** el sistema elimina todos los fragmentos de esa pieza del índice vectorial en la
  misma operación
- **AND** la pieza permanece visible en el sitio público

### Requirement: Atribución y sensibilidad

Cada `ContentItem` DEBE (MUST) registrar su modo de atribución con uno de estos valores:
`named`, `pseudonym` o `anonymous`. Cuando la atribución sea `anonymous`, el sistema NO
DEBE exponer el nombre de la persona testimoniante en ninguna respuesta de la API pública
ni en ninguna vista del sitio.

Cada `ContentItem` DEBE registrar un nivel de `sensitivity` con valor `normal` o `high`.

#### Scenario: Testimonio anónimo en la API pública

- **WHEN** un cliente solicita una pieza cuya atribución es `anonymous`
- **THEN** la respuesta no incluye el nombre real de la persona en ningún campo

#### Scenario: Testimonio con seudónimo

- **WHEN** una pieza tiene atribución `pseudonym`
- **THEN** el sistema muestra el seudónimo y no el nombre real

### Requirement: Texto alternativo obligatorio en contenido visual

Toda pieza de tipo `photo` DEBE (MUST) tener un campo `alt_text` no vacío. Todo `ContentItem`
que incluya una imagen destacada DEBE tener texto alternativo para esa imagen.

El sistema DEBE rechazar la publicación de una pieza visual sin texto alternativo.

#### Scenario: Intento de publicar una fotografía sin texto alternativo

- **WHEN** un editor intenta publicar una pieza de tipo `photo` con `alt_text` vacío o
  ausente
- **THEN** el sistema rechaza la publicación con un error que identifica el campo faltante

#### Scenario: Guardado como borrador sin texto alternativo

- **WHEN** un editor guarda como borrador una fotografía sin texto alternativo
- **THEN** el sistema permite guardar el borrador
- **AND** marca la pieza como no publicable hasta que se complete el campo

### Requirement: Estados de publicación

Cada `ContentItem` DEBE (MUST) tener un estado de publicación con uno de estos valores: `draft`,
`published` o `withdrawn`. Solo las piezas en estado `published` DEBEN ser visibles a
través de la API pública.

#### Scenario: Borrador invisible al público

- **WHEN** un cliente no autenticado consulta el listado de contenido de un tema
- **THEN** la respuesta incluye únicamente piezas en estado `published`

#### Scenario: Retiro de una pieza publicada

- **WHEN** un editor cambia una pieza de `published` a `withdrawn`
- **THEN** la pieza deja de aparecer en la API pública
- **AND** sus fragmentos se eliminan del índice vectorial

### Requirement: Procedencia del contenido importado

Todo `ContentItem` originado en el archivo previo DEBE (MUST) conservar un registro de
procedencia que incluya, como mínimo, el identificador o ruta de origen y la fecha de
importación.

#### Scenario: Trazabilidad de una pieza importada

- **WHEN** un administrador consulta una pieza importada desde el archivo
- **THEN** el sistema muestra de qué origen provino y cuándo fue importada
