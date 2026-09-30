## ADDED Requirements

### Requirement: Modelo de contenido geográfico

El sistema DEBE (MUST) representar el contenido geográfico como piezas de tipo `geo_item` capaces
de almacenar tres formas de geometría: punto, ruta y región.

El modelo DEBE quedar definido en esta fase aunque la visualización completa se difiera,
de modo que la fase 2 no requiera modificar el esquema.

#### Scenario: Registro de un punto

- **WHEN** un editor registra una organización o un servicio con sus coordenadas
- **THEN** el sistema almacena la pieza como geometría de punto

#### Scenario: Registro de una ruta

- **WHEN** un editor registra un trayecto con una secuencia de coordenadas
- **THEN** el sistema almacena la pieza como geometría de ruta

#### Scenario: Registro de un valor por región

- **WHEN** un editor registra un valor asociado a una entidad federativa o municipio
- **THEN** el sistema almacena la pieza como geometría de región con su valor asociado

### Requirement: Agregación obligatoria de datos sensibles

El sistema NO DEBE (MUST NOT) almacenar ni exponer coordenadas de punto exacto en una pieza
geográfica derivada de un testimonio marcado con `sensitivity` igual a `high`. Esa pieza
DEBE representarse únicamente mediante geometría de región a nivel de municipio o entidad
federativa.

Las geometrías de punto exacto SOLO DEBEN utilizarse para organizaciones, servicios y
espacios públicos.

#### Scenario: Intento de registrar un punto exacto desde un testimonio sensible

- **WHEN** un editor intenta registrar una geometría de punto para una pieza vinculada a un
  testimonio de sensibilidad alta
- **THEN** el sistema rechaza la operación e indica que debe usarse agregación por región

#### Scenario: Ausencia de coordenadas precisas en la API pública

- **WHEN** se auditan las respuestas públicas de contenido geográfico derivado de
  testimonios sensibles
- **THEN** ninguna expone coordenadas de punto exacto

#### Scenario: Punto exacto para una organización

- **WHEN** un editor registra la ubicación de una organización de apoyo
- **THEN** el sistema permite almacenar la geometría de punto exacto

### Requirement: Visualización mínima en esta fase

El sitio DEBE (MUST) presentar el contenido geográfico publicado de un tema mediante una
visualización de mapa mínima que muestre las geometrías registradas.

Las visualizaciones especializadas —mapas de rutas migratorias, coropléticos de incidencia
y capas de puntos de interés con interacción avanzada— quedan fuera de esta fase.

#### Scenario: Tema con contenido geográfico publicado

- **WHEN** una persona visita un tema que tiene piezas geográficas publicadas
- **THEN** el sistema muestra un mapa con las geometrías registradas

#### Scenario: Tema sin contenido geográfico

- **WHEN** un tema no tiene piezas geográficas publicadas
- **THEN** la sección de mapa se omite de la página temática

### Requirement: Alternativa textual al mapa

Todo mapa presentado en el sitio DEBE (MUST) ir acompañado de una representación textual
equivalente de la información que muestra, accesible mediante navegación por teclado y
lectores de pantalla.

#### Scenario: Consulta del mapa con lector de pantalla

- **WHEN** una persona recorre con lector de pantalla una página que incluye un mapa
- **THEN** puede acceder a la información del mapa en forma de lista o tabla equivalente
