## ADDED Requirements

### Requirement: Inventario del archivo existente

El sistema DEBE (MUST) proveer un proceso de inventario que recorra el material del archivo
previo y produzca un registro catalogado de cada elemento encontrado, incluyendo su ruta
de origen, tipo de medio detectado, tamaño y tema tentativo.

El inventario NO DEBE modificar ni mover el material original.

#### Scenario: Inventario de una carpeta del archivo

- **WHEN** se ejecuta el inventario sobre un directorio del archivo
- **THEN** el sistema produce un catálogo con una entrada por elemento encontrado
- **AND** el material original permanece intacto

#### Scenario: Elemento de formato no reconocido

- **WHEN** el inventario encuentra un archivo cuyo formato no puede clasificar
- **THEN** lo registra como no clasificado con su ruta de origen
- **AND** continúa procesando el resto sin interrumpirse

### Requirement: Organización del archivo en una raíz común por comunidad

El material del archivo DEBE (MUST) residir bajo una raíz común configurable, con
una subcarpeta por comunidad en el primer nivel cuyo nombre coincida con el
identificador del tema. Una segunda carpeta opcional indica el tipo de contenido.

    <raíz>/<comunidad>/<tipo>/documento.ext

El sistema DEBE ofrecer un comando que cree esa estructura, con exactamente una
carpeta por tipo de contenido, y que sea idempotente.

Al clasificar, la carpeta de tipo DEBE prevalecer sobre la extensión del archivo.
Cuando no exista carpeta de tipo, el tipo se deduce de la extensión.

El material NO DEBE versionarse en el repositorio bajo ninguna circunstancia.

#### Scenario: Creación de la estructura

- **WHEN** se ejecuta el comando de preparación del archivo
- **THEN** existe una carpeta por comunidad, cada una con una carpeta por tipo de
  contenido
- **AND** ejecutarlo de nuevo no crea ni modifica nada

#### Scenario: La carpeta manda sobre la extensión

- **WHEN** se encuentra un archivo `.txt` dentro de una carpeta de entrevistas
- **THEN** el sistema lo clasifica como entrevista y no como testimonio

#### Scenario: Carpeta de comunidad no reconocida

- **WHEN** el primer nivel de la ruta no corresponde a ninguna comunidad registrada
- **THEN** el sistema lo reporta como tal en lugar de asignarlo a una comunidad
  cualquiera

#### Scenario: Archivo suelto en la raíz

- **WHEN** existe un archivo directamente en la raíz, sin carpeta de comunidad
- **THEN** el sistema lo omite, porque no hay forma de saber a qué comunidad
  pertenece

### Requirement: Registro de documentos ya ingeridos

El sistema DEBE (MUST) mantener un registro persistente de los documentos del
archivo, independiente del catálogo de contenido, con al menos: ruta relativa,
comunidad, tipo detectado, huella del contenido, tamaño, fecha de modificación y
situación.

Un documento detectado y todavía no importado DEBE ser visible en ese registro.
El registro NO DEBE depender de que exista una pieza de contenido asociada.

#### Scenario: Documento detectado y sin importar

- **WHEN** se escanea un documento que aún no se incorpora al catálogo
- **THEN** aparece en el registro sin pieza de contenido asociada y marcado como
  pendiente de atención

#### Scenario: Registro de la procedencia

- **WHEN** se consulta un documento del registro
- **THEN** muestra su ruta de origen, cuándo se detectó por primera vez y cuándo
  se vio por última vez

### Requirement: Detección de altas, cambios y ausencias

Cada escaneo DEBE (MUST) comparar el árbol de archivos con el registro y
distinguir documentos nuevos, modificados, ausentes y sin cambios.

Un documento cuya huella de contenido cambió DEBE marcarse como modificado. Un
documento cuya fecha de modificación cambió pero cuyo contenido es idéntico NO
DEBE marcarse como modificado.

Un documento registrado que ya no aparece en el árbol DEBE marcarse como ausente,
sin eliminarse del registro.

Para evitar releer archivos que no cambiaron, el sistema PUEDE omitir el cálculo
de la huella cuando el tamaño y la fecha de modificación coincidan con lo
registrado, y DEBE ofrecer una opción para recalcularla de todos modos.

#### Scenario: Segundo escaneo sin cambios

- **WHEN** se escanea por segunda vez sin haber tocado el material
- **THEN** todos los documentos se reportan sin cambios
- **AND** no se recalcula la huella de ninguno

#### Scenario: Documento nuevo

- **WHEN** aparece un archivo que no estaba en el registro
- **THEN** el escaneo lo reporta como nuevo y lo incorpora al registro

#### Scenario: Documento modificado

- **WHEN** cambia el contenido de un archivo ya registrado
- **THEN** el escaneo lo reporta como modificado y actualiza su huella

#### Scenario: Archivo tocado sin cambiar su contenido

- **WHEN** cambia la fecha de modificación de un archivo pero su contenido es
  idéntico
- **THEN** el escaneo no lo reporta como modificado

#### Scenario: Documento ausente

- **WHEN** un documento registrado ya no aparece en el árbol de archivos
- **THEN** el escaneo lo marca como ausente y lo conserva en el registro

#### Scenario: Documento que reaparece

- **WHEN** un documento marcado como ausente vuelve a aparecer
- **THEN** el escaneo lo devuelve a pendiente de atención

#### Scenario: Material duplicado en dos rutas

- **WHEN** dos rutas distintas contienen contenido idéntico
- **THEN** ambos documentos comparten la misma huella, de modo que el duplicado
  sea detectable antes de importarlo dos veces

### Requirement: Reporte de escaneo accionable

Cada escaneo DEBE (MUST) producir un reporte con el conteo de documentos
recorridos, la lista de nuevos, modificados y ausentes, los conteos por comunidad
y por tipo, y las rutas cuya comunidad o tipo no se pudo determinar.

#### Scenario: Consulta del resultado de un escaneo

- **WHEN** finaliza un escaneo
- **THEN** el reporte indica qué apareció, qué cambió y qué desapareció desde el
  escaneo anterior

### Requirement: Transcripción por lotes del material audiovisual

El sistema DEBE (MUST) transcribir el material de audio y video mediante un modelo ejecutado en
infraestructura propia. El material audiovisual NO DEBE enviarse a servicios de
transcripción de terceros.

Cada transcripción DEBE producir, en una sola pasada: el texto plano destinado a la
indexación del chatbot, una pista de subtítulos en español con marcas de tiempo, y una
pista de subtítulos en inglés con marcas de tiempo.

#### Scenario: Transcripción de una entrevista en video

- **WHEN** se procesa una entrevista en video mediante el proceso de transcripción
- **THEN** el sistema genera el texto de la transcripción, la pista de subtítulos en
  español y la pista de subtítulos en inglés
- **AND** las tres salidas quedan asociadas a la misma pieza de contenido

#### Scenario: Material ya transcrito previamente

- **WHEN** el proceso encuentra material que ya cuenta con una transcripción proveniente
  del archivo original
- **THEN** el sistema conserva la transcripción existente y no la sobrescribe
- **AND** genera únicamente las pistas de subtítulos faltantes

#### Scenario: Confidencialidad de la transcripción

- **WHEN** se ejecuta la campaña de transcripción
- **THEN** ningún fragmento de audio, video o texto del archivo es enviado a un servicio
  externo

### Requirement: Importación normalizada al catálogo

El sistema DEBE (MUST) proveer un proceso de importación que convierta las entradas del
inventario en registros `ContentItem`, asignando `type`, `theme`, procedencia y
`consent_scope`.

La importación DEBE ser idempotente: ejecutarla dos veces sobre el mismo origen NO DEBE
producir piezas duplicadas.

#### Scenario: Importación de un lote de material

- **WHEN** se importa un lote inventariado
- **THEN** el sistema crea un `ContentItem` por elemento con su procedencia registrada

#### Scenario: Reejecución de la importación

- **WHEN** se ejecuta la importación por segunda vez sobre el mismo origen
- **THEN** el sistema actualiza los registros existentes y no crea duplicados

#### Scenario: Consentimiento no determinable durante la importación

- **WHEN** una pieza se importa sin información explícita de consentimiento
- **THEN** el sistema le asigna `consent_scope` igual a `no_ai`
- **AND** la marca para revisión manual por parte del equipo

#### Scenario: Elemento que falla durante la importación

- **WHEN** un elemento del lote falla al importarse
- **THEN** el sistema registra el error con la ruta de origen y la causa
- **AND** completa la importación del resto del lote

### Requirement: Reporte de importación

Al finalizar cada ejecución, el proceso de importación DEBE (MUST) producir un reporte con el
número de piezas creadas, actualizadas, omitidas y fallidas, desglosado por tema y por
tipo de contenido.

#### Scenario: Consulta del resultado de una importación

- **WHEN** finaliza una ejecución de importación
- **THEN** el sistema entrega un reporte con los conteos por tema y por tipo, y el detalle
  de los elementos fallidos
