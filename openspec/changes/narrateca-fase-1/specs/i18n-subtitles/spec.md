## ADDED Requirements

### Requirement: Interfaz bilingüe con español como idioma principal

La interfaz del sitio DEBE (MUST) estar disponible en español e inglés. El español DEBE ser el
idioma por defecto.

Cada idioma DEBE tener su propia dirección, de modo que una página en un idioma
determinado sea enlazable directamente.

El contenido escrito del archivo —testimonios, entrevistas y notas— permanece en español y
NO DEBE traducirse automáticamente.

#### Scenario: Ingreso sin preferencia de idioma

- **WHEN** una persona ingresa al sitio sin indicar idioma
- **THEN** el sistema presenta la interfaz en español

#### Scenario: Cambio de idioma de la interfaz

- **WHEN** una persona cambia el idioma a inglés desde cualquier página
- **THEN** los elementos de interfaz se muestran en inglés
- **AND** permanece en la página equivalente sin volver al inicio

#### Scenario: Enlace directo a una página en inglés

- **WHEN** se abre la dirección de una página en inglés
- **THEN** el sistema la presenta con la interfaz en inglés

#### Scenario: Contenido del archivo sin traducir

- **WHEN** se consulta un testimonio con la interfaz en inglés
- **THEN** el texto del testimonio se muestra en español, sin traducción automática

### Requirement: Idioma declarado en el marcado

Cada página DEBE (MUST) declarar su idioma en el marcado. Cuando un bloque de contenido esté en
un idioma distinto al de la página, ese bloque DEBE declarar su propio idioma.

#### Scenario: Testimonio en español dentro de una página en inglés

- **WHEN** una página con interfaz en inglés muestra un testimonio en español
- **THEN** el bloque del testimonio declara español como su idioma
- **AND** un lector de pantalla puede pronunciarlo correctamente

### Requirement: Subtítulos en español e inglés para todo el material audiovisual

Todo `ContentItem` de tipo `video` o con audio asociado DEBE (MUST) contar con una pista de
subtítulos en español y una pista de subtítulos en inglés antes de poder publicarse.

Los subtítulos en español cumplen una función de accesibilidad; los subtítulos en inglés
cumplen una función de traducción.

#### Scenario: Publicación de un video con ambas pistas

- **WHEN** un editor publica un video que cuenta con pistas de subtítulos en español e
  inglés
- **THEN** el sistema permite la publicación
- **AND** ambas pistas quedan disponibles en el reproductor

#### Scenario: Intento de publicar un video sin subtítulos

- **WHEN** un editor intenta publicar un video sin pista de subtítulos en español
- **THEN** el sistema rechaza la publicación indicando la pista faltante

#### Scenario: Selección de pista por la persona usuaria

- **WHEN** una persona reproduce un video publicado
- **THEN** puede activar los subtítulos y elegir entre español e inglés

### Requirement: Origen de los subtítulos en la transcripción

Las pistas de subtítulos DEBEN (MUST) generarse a partir de la transcripción producida en
infraestructura propia, y DEBEN ser editables por el equipo para corregir errores del
proceso automático.

#### Scenario: Corrección manual de una pista

- **WHEN** un editor corrige el texto de una pista de subtítulos generada automáticamente
- **THEN** el sistema conserva la corrección y la sirve en lugar de la versión automática

#### Scenario: Confidencialidad de la generación de subtítulos

- **WHEN** se generan las pistas de subtítulos de una pieza
- **THEN** el audio y el texto no se transmiten a servicios externos
