## ADDED Requirements

### Requirement: Panel de salud del archivo

El panel de control DEBE (MUST) mostrar el conteo de piezas de contenido desglosado por tema y
por tipo de contenido, distinguiendo entre estados de publicación.

#### Scenario: Consulta de la composición del archivo

- **WHEN** una cuenta administradora abre el panel de control
- **THEN** ve cuántas piezas hay por tema y por tipo, y en qué estado de publicación se
  encuentran

#### Scenario: Identificación de un tema con poco material

- **WHEN** un tema tiene notablemente menos contenido publicado que los demás
- **THEN** la diferencia es visible en el panel sin necesidad de exportar datos

### Requirement: Cobertura del índice del chatbot

El panel DEBE (MUST) mostrar, por cada tema, cuántas piezas están publicadas, cuántas están
indexadas, cuántas están excluidas por `consent_scope` igual a `no_ai`, y cuántas tienen
fragmentos con revisión pendiente.

#### Scenario: Consulta de cobertura por tema

- **WHEN** una cuenta administradora consulta la cobertura del índice
- **THEN** ve para cada tema los conteos de publicadas, indexadas, excluidas y pendientes
  de revisión

#### Scenario: Divergencia entre publicado e indexado

- **WHEN** existen piezas publicadas e indexables que no están en el índice
- **THEN** el panel expone esa diferencia de forma visible

### Requirement: Estado de activación de cada persona

El panel DEBE (MUST) mostrar el estado de activación de cada una de las cuatro personas y el
tamaño de su corpus, de modo que sea posible saber cuánto falta para activarla.

#### Scenario: Consulta del estado de las personas

- **WHEN** una cuenta administradora consulta el panel
- **THEN** ve el estado de activación de cada comunidad y el tamaño de su corpus

### Requirement: Actividad del chatbot

El panel DEBE (MUST) mostrar el volumen de conversaciones por tema y por periodo, y DEBE listar
los turnos en los que el sistema respondió que no contaba con material relevante.

#### Scenario: Consulta del volumen de conversaciones

- **WHEN** una cuenta administradora consulta la actividad del chatbot
- **THEN** ve el número de conversaciones por tema en el periodo seleccionado

#### Scenario: Detección de vacíos en el archivo

- **WHEN** una cuenta administradora revisa los turnos sin material relevante
- **THEN** puede identificar qué se está preguntando y no está cubierto por el archivo

### Requirement: Fragmentos más recuperados

El panel DEBE (MUST) listar los fragmentos recuperados con mayor frecuencia por tema, con enlace
a su pieza de origen.

#### Scenario: Consulta de fragmentos más usados

- **WHEN** una cuenta administradora consulta los fragmentos más recuperados de un tema
- **THEN** ve la lista ordenada por frecuencia con enlace a cada pieza de origen

### Requirement: Conteo de mensajes de contención

El panel DEBE (MUST) mostrar el número de turnos marcados con mensaje de contención por tema y
por periodo, sin exponer el contenido de esos mensajes en la vista agregada.

#### Scenario: Consulta agregada de contención

- **WHEN** una cuenta administradora consulta el panel
- **THEN** ve el conteo de turnos con contención por tema
- **AND** la vista agregada no muestra el texto de los mensajes de las personas usuarias

### Requirement: Acceso restringido al panel de control

El panel de control SOLO DEBE (MUST) ser accesible a cuentas autenticadas con rol de
administrador.

#### Scenario: Acceso de una cuenta editora

- **WHEN** una cuenta con rol `editor` intenta abrir el panel de control
- **THEN** el sistema deniega el acceso

#### Scenario: Acceso sin autenticación

- **WHEN** una persona sin sesión solicita los datos del panel de control
- **THEN** el sistema deniega el acceso
