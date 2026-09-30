## ADDED Requirements

### Requirement: Generación local de representaciones vectoriales

El sistema DEBE (MUST) generar las representaciones vectoriales del contenido y de las consultas
mediante un modelo de embeddings ejecutado en infraestructura propia.

El sistema NO DEBE enviar el texto del archivo a servicios de embeddings de terceros.

El modelo de embeddings DEBE ser multilingüe, de modo que una consulta en inglés recupere
fragmentos escritos en español.

#### Scenario: Indexación de una pieza de contenido

- **WHEN** el sistema genera los vectores de una pieza para indexarla
- **THEN** el cálculo ocurre en infraestructura propia
- **AND** el texto de la pieza no se transmite a ningún servicio externo

#### Scenario: Recuperación desde una consulta en inglés

- **WHEN** se genera el vector de una consulta escrita en inglés
- **THEN** la búsqueda recupera fragmentos relevantes escritos en español

### Requirement: Segmentación e indexación particionada por tema

El sistema DEBE (MUST) segmentar el texto de cada pieza indexable en fragmentos y almacenarlos en
un índice vectorial particionado por `theme`.

Cada fragmento DEBE conservar la referencia a su `ContentItem` de origen, de modo que
siempre sea posible construir el enlace a la pieza original.

Una búsqueda dirigida a un tema NO DEBE devolver fragmentos pertenecientes a otro tema.

#### Scenario: Aislamiento entre corpus temáticos

- **WHEN** se ejecuta una búsqueda sobre el corpus del tema de migrantes
- **THEN** todos los fragmentos devueltos pertenecen a piezas cuyo `theme` es migrantes

#### Scenario: Trazabilidad de un fragmento recuperado

- **WHEN** el sistema recupera un fragmento
- **THEN** puede resolver el identificador de la pieza de origen y su dirección pública

### Requirement: Respeto del alcance de consentimiento en la indexación

El sistema NO DEBE (MUST NOT) generar ni almacenar fragmentos indexables de ninguna pieza cuyo
`consent_scope` sea `no_ai`.

#### Scenario: Pieza excluida por consentimiento

- **WHEN** se procesa para indexación una pieza con `consent_scope` igual a `no_ai`
- **THEN** el sistema omite la pieza y no crea ningún fragmento para ella

#### Scenario: Verificación del índice frente al consentimiento

- **WHEN** se audita el índice vectorial completo
- **THEN** no existe ningún fragmento perteneciente a una pieza marcada como `no_ai`

### Requirement: Ingesta automática al publicar con revisión posterior

Al publicarse una pieza cuyo `consent_scope` lo permita, el sistema DEBE (MUST) segmentarla,
generar sus vectores e incorporarla al índice de su tema de forma automática.

Todo fragmento recién incorporado DEBE quedar marcado con estado de revisión `pending`
hasta que una cuenta autorizada lo apruebe o lo retire.

#### Scenario: Publicación de una pieza indexable

- **WHEN** un editor publica un testimonio con `consent_scope` igual a `public`
- **THEN** el sistema lo incorpora al índice del tema correspondiente
- **AND** sus fragmentos quedan marcados como revisión pendiente

#### Scenario: Aprobación de contenido indexado

- **WHEN** una cuenta autorizada aprueba los fragmentos de una pieza
- **THEN** su estado de revisión pasa a aprobado y permanecen en el índice

#### Scenario: Retiro de contenido desde la revisión

- **WHEN** una cuenta autorizada retira del índice los fragmentos de una pieza
- **THEN** el sistema los elimina del índice vectorial
- **AND** la pieza permanece publicada en el sitio público

### Requirement: Sincronización del índice ante cambios de contenido

El sistema DEBE (MUST) actualizar o eliminar los fragmentos de una pieza en la misma
operación en que esta se edita, se retira, se elimina o cambia su `consent_scope` a `no_ai`,
de modo que el índice nunca contenga contenido que ya no está publicado.

#### Scenario: Edición de una pieza indexada

- **WHEN** un editor modifica el texto de una pieza ya indexada
- **THEN** el sistema regenera sus fragmentos y reemplaza los anteriores

#### Scenario: Eliminación de una pieza indexada

- **WHEN** un editor elimina una pieza que estaba indexada
- **THEN** el sistema elimina todos sus fragmentos del índice

#### Scenario: Ausencia de contenido huérfano en el índice

- **WHEN** se audita el índice vectorial
- **THEN** todo fragmento corresponde a una pieza existente en estado `published` cuyo
  `consent_scope` no es `no_ai`

### Requirement: Reconstrucción del índice desde la fuente de verdad

El sistema DEBE (MUST) permitir reconstruir por completo el índice vectorial a partir del
contenido almacenado en la base de datos relacional, que es la fuente de verdad.

#### Scenario: Reconstrucción completa del índice

- **WHEN** se ejecuta la reconstrucción del índice de un tema
- **THEN** el índice resultante contiene exactamente los fragmentos de las piezas
  publicadas e indexables de ese tema
