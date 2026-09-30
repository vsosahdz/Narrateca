## ADDED Requirements

### Requirement: Sección de noticias por tema

Cada página temática DEBE (MUST) incluir una sección de noticias que muestre las piezas de tipo
`news_post` y `curated_link` publicadas para ese tema, ordenadas de la más reciente a la
más antigua.

#### Scenario: Consulta de la sección de noticias

- **WHEN** una persona visita la sección de noticias de un tema
- **THEN** ve las notas y enlaces curados publicados de ese tema, con la más reciente
  primero

#### Scenario: Tema sin noticias publicadas

- **WHEN** un tema no tiene noticias publicadas
- **THEN** la sección de noticias se omite de la página temática

### Requirement: Notas redactadas por el equipo

El sistema DEBE (MUST) permitir que un editor redacte y publique una nota propia con título,
cuerpo, fecha de publicación e imagen destacada opcional, asociada a un tema.

Cuando la nota incluya imagen destacada, esta DEBE tener texto alternativo no vacío para
poder publicarse.

#### Scenario: Publicación de una nota propia

- **WHEN** un editor redacta una nota con título, cuerpo y fecha y la publica
- **THEN** la nota aparece en la sección de noticias de su tema

#### Scenario: Nota con imagen sin texto alternativo

- **WHEN** un editor intenta publicar una nota cuya imagen destacada carece de texto
  alternativo
- **THEN** el sistema rechaza la publicación indicando el campo faltante

### Requirement: Enlaces curados a medios externos

El sistema DEBE (MUST) permitir registrar un enlace a una nota publicada en un medio externo,
acompañado de un título, el nombre del medio, la fecha y un resumen redactado por el
equipo.

El sistema NO DEBE almacenar ni republicar el cuerpo completo del artículo externo.

#### Scenario: Registro de un enlace curado

- **WHEN** un editor registra un enlace externo con su título, medio, fecha y resumen propio
- **THEN** el sistema lo publica en la sección de noticias del tema correspondiente
- **AND** el enlace apunta a la publicación original en el medio externo

#### Scenario: Enlace curado sin resumen propio

- **WHEN** un editor intenta publicar un enlace curado sin resumen redactado
- **THEN** el sistema rechaza la publicación indicando que el resumen es obligatorio

#### Scenario: Distinción visible entre contenido propio y externo

- **WHEN** una persona ve la sección de noticias
- **THEN** puede distinguir cuáles piezas son notas del equipo y cuáles son enlaces a
  medios externos

### Requirement: Ausencia de agregación automática

El sistema NO DEBE (MUST NOT) recolectar, importar ni clasificar noticias de fuentes externas de
forma automática. Toda pieza de la sección de noticias DEBE originarse en una acción
explícita de un editor autenticado.

#### Scenario: Origen de toda noticia publicada

- **WHEN** se audita el origen de las piezas de la sección de noticias
- **THEN** cada una registra al editor que la creó y la fecha de creación
