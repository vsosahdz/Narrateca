## ADDED Requirements

### Requirement: Aviso de privacidad previo al primer mensaje

El sistema DEBE (MUST) mostrar un aviso antes de que la persona usuaria envíe su primer mensaje,
que indique que conversa con un sistema automatizado, que las conversaciones se guardan de
forma anónima y con qué finalidad.

La persona DEBE poder leer el aviso sin haber enviado ningún mensaje.

#### Scenario: Primera visita a la página del chatbot

- **WHEN** una persona abre la página del chatbot por primera vez
- **THEN** ve el aviso antes de poder enviar un mensaje

#### Scenario: Contenido del aviso

- **WHEN** se muestra el aviso
- **THEN** informa que se trata de un sistema automatizado, que las conversaciones se
  almacenan de forma anónima y para qué se utilizan

### Requirement: Persistencia anónima de conversaciones

El sistema DEBE (MUST) almacenar cada conversación con un identificador de sesión efímero, los
mensajes de la persona usuaria y las respuestas generadas, junto con el tema de la
comunidad y las marcas de tiempo.

El sistema NO DEBE almacenar la dirección IP, el identificador del navegador, ni ningún
dato que permita reidentificar a la persona usuaria.

El identificador de sesión NO DEBE persistir entre visitas ni permitir vincular
conversaciones distintas de una misma persona.

#### Scenario: Registro de una conversación

- **WHEN** una persona sostiene una conversación con una comunidad
- **THEN** el sistema almacena los turnos de la conversación asociados al tema y a un
  identificador de sesión

#### Scenario: Ausencia de datos identificatorios

- **WHEN** se inspecciona un registro de conversación almacenado
- **THEN** no contiene dirección IP, huella de navegador ni identificador de persona usuaria

#### Scenario: Visitas separadas de una misma persona

- **WHEN** una misma persona conversa en dos visitas distintas
- **THEN** el sistema no puede vincular ambas conversaciones entre sí

### Requirement: Registro de los fragmentos recuperados por turno

Por cada respuesta generada, el sistema DEBE (MUST) almacenar los identificadores de los
fragmentos recuperados y las puntuaciones de relevancia obtenidas, con el propósito de
evaluar y depurar la calidad de la recuperación.

#### Scenario: Depuración de una respuesta

- **WHEN** una cuenta administradora revisa una respuesta almacenada
- **THEN** puede consultar qué fragmentos se recuperaron y con qué relevancia

#### Scenario: Respuesta sin material suficiente

- **WHEN** el sistema responde que no cuenta con material sobre una pregunta
- **THEN** almacena el turno marcado como sin recuperación relevante

### Requirement: Marcado de turnos con mensaje de contención

El sistema DEBE (MUST) marcar el turno con el indicador correspondiente en el registro
cuando responda con un mensaje de contención por detección de revelación personal.

El registro NO DEBE incorporar ninguna categorización adicional de la persona usuaria más
allá de ese indicador.

#### Scenario: Turno con contención registrado

- **WHEN** el sistema emite un mensaje de contención
- **THEN** el turno queda marcado con ese indicador en el registro almacenado

### Requirement: Acceso restringido a los registros de conversación

Los registros de conversación SOLO DEBEN (MUST) ser accesibles a cuentas autenticadas con rol de
administrador. No DEBEN exponerse a través de ningún endpoint público.

#### Scenario: Solicitud pública de registros

- **WHEN** una persona sin autenticación solicita registros de conversación
- **THEN** el sistema deniega el acceso

#### Scenario: Consulta por una cuenta editora

- **WHEN** una cuenta con rol `editor` solicita registros de conversación
- **THEN** el sistema deniega el acceso

### Requirement: Retención y eliminación de registros

El sistema DEBE (MUST) permitir configurar un periodo de retención y DEBE ofrecer un mecanismo
para eliminar de forma permanente los registros que lo excedan.

#### Scenario: Eliminación de registros vencidos

- **WHEN** se ejecuta el proceso de retención con un periodo configurado
- **THEN** el sistema elimina de forma permanente los registros anteriores a ese periodo
