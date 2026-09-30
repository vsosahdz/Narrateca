## ADDED Requirements

### Requirement: Página de inicio con los cuatro temas

El sitio DEBE (MUST) presentar una página de inicio que muestre los cuatro temas —migrantes,
comunidad LGBTQ+, mujeres con discapacidad, y mujeres y violencia de género— cada uno con
acceso directo a su página independiente.

La página de inicio NO DEBE incluir botones, enlaces ni formularios de donación.

#### Scenario: Ingreso al sitio

- **WHEN** una persona visita la raíz del sitio
- **THEN** ve los cuatro temas presentados con su título, imagen y descripción breve
- **AND** cada uno enlaza a su página temática

#### Scenario: Ausencia de donaciones

- **WHEN** se revisa cualquier página del sitio público
- **THEN** no existe ningún elemento de donación, aporte económico o pasarela de pago

### Requirement: Página independiente por tema

Cada uno de los cuatro temas DEBE (MUST) tener su propia página, servida en una ruta propia, que
presente el contenido publicado de ese tema agrupado por tipo: fotografías, testimonios,
videos, entrevistas y noticias.

Una página temática DEBE mostrar únicamente contenido cuyo `theme` corresponda a ese tema
y cuyo estado de publicación sea `published`.

#### Scenario: Consulta de una página temática

- **WHEN** una persona visita la página de un tema
- **THEN** ve el contenido publicado de ese tema, agrupado por tipo de contenido

#### Scenario: Aislamiento entre temas

- **WHEN** se carga la página de un tema
- **THEN** no aparece contenido perteneciente a otro tema

#### Scenario: Tema sin contenido de un tipo

- **WHEN** un tema no tiene ninguna pieza publicada de un tipo determinado
- **THEN** la sección correspondiente se omite en lugar de mostrarse vacía

### Requirement: Filtrado por tipo de contenido

Cada página temática DEBE (MUST) permitir filtrar el contenido por tipo. El sitio NO requiere
búsqueda por texto libre en esta fase.

#### Scenario: Filtrado dentro de un tema

- **WHEN** una persona filtra la página de un tema por un tipo de contenido
- **THEN** la vista muestra únicamente las piezas publicadas de ese tipo dentro de ese tema

### Requirement: Página de detalle de una pieza con enlace estable

Cada pieza publicada DEBE (MUST) ser accesible en una dirección propia y estable, de modo que
pueda enlazarse y citarse desde el chatbot y desde fuera del sitio.

#### Scenario: Acceso directo a un testimonio

- **WHEN** una persona abre la dirección de un testimonio publicado
- **THEN** el sistema muestra la pieza completa con su atribución y su contenido asociado

#### Scenario: Acceso a una pieza retirada

- **WHEN** una persona abre la dirección de una pieza en estado `withdrawn`
- **THEN** el sistema responde que el contenido no está disponible y no expone su contenido

### Requirement: Página del equipo de investigación

El sitio DEBE (MUST) incluir una página dedicada al equipo de investigación que muestre, por cada
integrante, su fotografía, su nombre y su biografía.

La fotografía de cada integrante DEBE tener texto alternativo no vacío.

#### Scenario: Consulta de la página del equipo

- **WHEN** una persona visita la página del equipo de investigación
- **THEN** ve a cada integrante con su fotografía, nombre y biografía

#### Scenario: Integrante sin fotografía

- **WHEN** un integrante no tiene fotografía cargada
- **THEN** el sistema muestra su nombre y biografía con un marcador visual neutro en lugar
  de una imagen rota

### Requirement: Cimientos de accesibilidad en el sitio público

Todo el sitio público DEBE (MUST) usar marcado semántico con jerarquía de encabezados coherente,
DEBE ser operable únicamente con teclado, y todos sus controles interactivos DEBEN ser
alcanzables mediante navegación por tabulador con indicador de foco visible.

Todas las imágenes DEBEN exponer su texto alternativo.

#### Scenario: Navegación completa por teclado

- **WHEN** una persona navega cualquier página del sitio usando solo el teclado
- **THEN** puede alcanzar y activar todos los controles interactivos
- **AND** el elemento enfocado es visualmente identificable en todo momento

#### Scenario: Imagen expuesta a tecnología de asistencia

- **WHEN** un lector de pantalla recorre una página con fotografías
- **THEN** anuncia el texto alternativo registrado para cada imagen

### Requirement: Reproducción de video según sensibilidad

El sitio DEBE (MUST) reproducir el material de video mediante un reproductor propio cuando la
pieza esté marcada con `sensitivity` igual a `high`, sin incrustar servicios de video de
terceros para ese material.

El material de difusión general con `sensitivity` igual a `normal` PUEDE reproducirse
mediante un servicio de video externo.

#### Scenario: Video de testimonio sensible

- **WHEN** se reproduce un video de una pieza marcada como sensibilidad alta
- **THEN** el sistema lo sirve desde su propio almacenamiento con reproductor propio
- **AND** no se carga ningún reproductor incrustado de terceros

#### Scenario: Video de difusión general

- **WHEN** se reproduce un video de sensibilidad normal alojado en un servicio externo
- **THEN** el sistema lo presenta mediante el reproductor de ese servicio
