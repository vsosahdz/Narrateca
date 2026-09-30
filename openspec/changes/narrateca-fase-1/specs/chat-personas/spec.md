## ADDED Requirements

### Requirement: Configuración de persona por comunidad

El sistema DEBE (MUST) definir una configuración de persona independiente por cada tema, que
incluya como mínimo: el prompt de sistema, el identificador del corpus del que recupera,
la política de voz, la política de seguridad, el idioma base y el estado de activación.

Las configuraciones DEBEN ser modificables sin cambios en el código de la aplicación.

La política de voz DEBE modelarse aunque la síntesis de voz no se implemente en esta fase,
y DEBE registrar que los temas de mujeres con discapacidad y de mujeres y violencia de
género admiten exclusivamente voz femenina, mientras que los temas de migrantes y
comunidad LGBTQ+ admiten voz femenina o masculina.

#### Scenario: Personas independientes por tema

- **WHEN** una persona conversa con la comunidad de migrantes
- **THEN** el sistema aplica el prompt de sistema y el corpus configurados para ese tema, y
  no los de otro

#### Scenario: Modificación de una configuración de persona

- **WHEN** una cuenta administradora modifica el prompt de sistema de una persona
- **THEN** las conversaciones posteriores usan el prompt actualizado sin necesidad de
  desplegar código

#### Scenario: Política de voz registrada

- **WHEN** se consulta la configuración de la persona del tema de mujeres y violencia de
  género
- **THEN** su política de voz admite exclusivamente voz femenina

### Requirement: Activación independiente por comunidad

Cada persona DEBE (MUST) tener un estado de activación con uno de estos valores: `draft`,
`coming_soon` o `active`. Solo una persona en estado `active` DEBE aceptar conversaciones
del público.

El estado de una comunidad NO DEBE depender del estado de las demás.

El selector público DEBE mostrar las cuatro comunidades en todo momento, señalando cuáles
aún no están disponibles.

#### Scenario: Conversación con una comunidad activa

- **WHEN** una persona selecciona una comunidad en estado `active`
- **THEN** el sistema le permite conversar

#### Scenario: Intento de conversación con una comunidad no activa

- **WHEN** una persona intenta iniciar una conversación con una comunidad en estado
  `coming_soon`
- **THEN** el sistema no genera respuesta y comunica que esa comunidad estará disponible
  próximamente

#### Scenario: Selector con comunidades en estados distintos

- **WHEN** dos comunidades están activas y dos están en `coming_soon`
- **THEN** el selector muestra las cuatro, y solo permite iniciar conversación con las dos
  activas

#### Scenario: Persona en borrador

- **WHEN** una persona está en estado `draft`
- **THEN** solo las cuentas autenticadas de administración pueden conversar con ella

### Requirement: Respuesta anclada en fragmentos recuperados

Toda respuesta del chatbot DEBE (MUST) construirse a partir de fragmentos recuperados del corpus
de la comunidad seleccionada.

El sistema NO DEBE afirmar hechos concretos —nombres, fechas, lugares, cifras o
acontecimientos— que no provengan de un fragmento recuperado.

Cuando la recuperación no devuelva fragmentos suficientemente relevantes, el sistema DEBE
declarar que no cuenta con material sobre esa pregunta, en lugar de generar una respuesta.

#### Scenario: Pregunta con material disponible

- **WHEN** una persona pregunta sobre un tema cubierto por el corpus
- **THEN** la respuesta se apoya en fragmentos recuperados y los cita

#### Scenario: Pregunta sin material disponible

- **WHEN** la recuperación no devuelve fragmentos relevantes para la pregunta
- **THEN** el sistema responde que no cuenta con testimonios sobre ese punto
- **AND** no genera afirmaciones sobre el tema preguntado

#### Scenario: Ausencia de biografía inventada

- **WHEN** una persona pide datos personales de la voz con la que conversa, como su nombre
  o su edad
- **THEN** el sistema aclara que representa las voces del archivo de esa comunidad y no a
  una persona individual

### Requirement: Citación en línea con enlace a la pieza original

Cada afirmación sustentada en el corpus DEBE (MUST) presentarse con el fragmento textual citado y
un enlace a la dirección pública de la pieza de origen.

Los enlaces citados DEBEN apuntar a piezas en estado `published`.

#### Scenario: Respuesta con citas

- **WHEN** el sistema responde apoyándose en dos fragmentos de piezas distintas
- **THEN** la respuesta incluye ambos fragmentos citados textualmente con su enlace a la
  pieza correspondiente

#### Scenario: Validez de los enlaces citados

- **WHEN** se sigue un enlace de una cita entregada por el chatbot
- **THEN** conduce a la pieza de origen en el sitio público

### Requirement: Respuesta en el idioma de la persona usuaria

El sistema DEBE (MUST) detectar el idioma del mensaje y responder en español o en inglés según
corresponda, recuperando del corpus en español en ambos casos.

Las citas textuales DEBEN presentarse en su idioma original. Cuando la respuesta esté en
inglés, una cita en español DEBE mostrarse en español acompañada de su traducción,
identificada como traducción.

#### Scenario: Pregunta en inglés

- **WHEN** una persona escribe su pregunta en inglés
- **THEN** el sistema responde en inglés
- **AND** recupera fragmentos del corpus en español

#### Scenario: Cita en respuesta en inglés

- **WHEN** una respuesta en inglés incluye una cita textual de un testimonio en español
- **THEN** la cita se muestra en español junto a su traducción, señalada como traducción

#### Scenario: Pregunta en español

- **WHEN** una persona escribe su pregunta en español
- **THEN** el sistema responde en español

### Requirement: Mensaje de contención ante revelaciones personales

El sistema DEBE (MUST) responder con un mensaje breve de contención cuando detecte que la
persona usuaria relata una experiencia personal de violencia, riesgo o crisis. Ese mensaje
DEBE reconocer lo expresado y recordar que está conversando con un sistema automatizado.

En ese caso el sistema NO DEBE continuar el rol de persona, NO DEBE ofrecer consejo
clínico, legal ni terapéutico, y NO DEBE emitir diagnósticos.

#### Scenario: Relato de una experiencia personal de violencia

- **WHEN** una persona relata al chatbot una experiencia propia de violencia
- **THEN** el sistema responde con un mensaje de contención que reconoce lo dicho y aclara
  que se trata de un sistema automatizado
- **AND** no emite consejo clínico, legal ni terapéutico

#### Scenario: Solicitud de asesoría profesional

- **WHEN** una persona pide al chatbot indicaciones sobre qué hacer ante una situación de
  riesgo personal
- **THEN** el sistema aclara que no puede brindar asesoría y no la proporciona

### Requirement: Transmisión progresiva de la respuesta

El sistema DEBE (MUST) transmitir la respuesta de forma progresiva a medida que se genera, para
que la persona usuaria vea avance sin esperar a la respuesta completa.

#### Scenario: Recepción progresiva

- **WHEN** el sistema genera una respuesta
- **THEN** el texto llega a la interfaz de forma incremental antes de completarse

### Requirement: Proveedor de modelo intercambiable

El sistema DEBE (MUST) acceder al modelo de lenguaje a través de una interfaz con implementación
seleccionable y punto de conexión configurable, de modo que cambiar de proveedor o mover
la inferencia a infraestructura propia no requiera modificar la lógica del chat.

#### Scenario: Cambio de proveedor por configuración

- **WHEN** se modifica la configuración del proveedor y su punto de conexión
- **THEN** el sistema utiliza el nuevo proveedor sin cambios en los módulos de recuperación,
  citación ni persistencia

### Requirement: Minimización de datos enviados al proveedor de lenguaje

En cada intercambio, el sistema SOLO DEBE (MUST) enviar al proveedor de modelo de lenguaje el
prompt de sistema de la persona, el historial de la conversación en curso y los fragmentos
recuperados para esa consulta.

El sistema NO DEBE enviar el corpus completo, ni piezas no recuperadas, ni contenido cuyo
`consent_scope` sea `no_ai`.

#### Scenario: Contenido enviado en una consulta

- **WHEN** se procesa una pregunta que recupera cuatro fragmentos
- **THEN** la solicitud al proveedor contiene únicamente esos cuatro fragmentos, el
  historial de la conversación y el prompt de sistema

#### Scenario: Contenido excluido nunca transmitido

- **WHEN** se audita el contenido enviado al proveedor a lo largo de múltiples
  conversaciones
- **THEN** ningún fragmento proviene de una pieza marcada como `no_ai`
