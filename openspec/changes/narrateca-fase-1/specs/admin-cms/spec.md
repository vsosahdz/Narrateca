## ADDED Requirements

### Requirement: Autenticación con cuentas propias

El sistema DEBE (MUST) autenticar a las personas administradoras mediante cuentas propias con
correo electrónico y contraseña. Las contraseñas DEBEN almacenarse únicamente como hash
con un algoritmo de derivación de clave resistente a fuerza bruta, y NUNCA en texto claro
ni cifradas de forma reversible.

Toda la sección de administración DEBE requerir autenticación.

#### Scenario: Ingreso con credenciales válidas

- **WHEN** una persona administradora ingresa su correo y contraseña correctos
- **THEN** el sistema le otorga una sesión autenticada con su rol asociado

#### Scenario: Ingreso con credenciales inválidas

- **WHEN** se ingresan credenciales incorrectas
- **THEN** el sistema rechaza el acceso sin revelar si el correo existe o no

#### Scenario: Acceso sin sesión a la administración

- **WHEN** una persona sin sesión autenticada solicita cualquier recurso de administración
- **THEN** el sistema deniega el acceso y no expone datos de contenido no publicado

#### Scenario: Almacenamiento de contraseñas

- **WHEN** se inspecciona el registro de una cuenta en la base de datos
- **THEN** la contraseña aparece únicamente como hash y no es reversible

### Requirement: Roles de administrador y editor por tema

El sistema DEBE (MUST) soportar dos roles: `admin` y `editor`. Una cuenta con rol `editor` DEBE
tener asignados uno o más temas y solo DEBE poder crear, editar, publicar y retirar
contenido de los temas que tiene asignados.

Una cuenta con rol `admin` DEBE poder operar sobre todos los temas y además gestionar
cuentas y configuración.

#### Scenario: Editor operando en su tema asignado

- **WHEN** un editor asignado al tema de migrantes edita una pieza de ese tema
- **THEN** el sistema aplica el cambio

#### Scenario: Editor intentando operar fuera de su tema

- **WHEN** un editor asignado únicamente al tema de migrantes intenta editar una pieza del
  tema de mujeres y violencia de género
- **THEN** el sistema deniega la operación y no modifica la pieza

#### Scenario: Editor intentando gestionar cuentas

- **WHEN** una cuenta con rol `editor` intenta crear, modificar o eliminar cuentas de
  usuario
- **THEN** el sistema deniega la operación

#### Scenario: Administrador operando en cualquier tema

- **WHEN** una cuenta con rol `admin` edita contenido de cualquiera de los cuatro temas
- **THEN** el sistema aplica el cambio

### Requirement: Operaciones de contenido desde el panel

El panel DEBE (MUST) permitir crear, editar, publicar, retirar y eliminar piezas de contenido de
todos los tipos soportados, así como cargar los archivos de media asociados.

#### Scenario: Publicación de contenido nuevo

- **WHEN** un editor autorizado crea una pieza válida y la publica
- **THEN** la pieza pasa a estado `published` y aparece en el sitio público

#### Scenario: Retiro de contenido publicado

- **WHEN** un editor autorizado retira una pieza publicada
- **THEN** la pieza pasa a estado `withdrawn` y deja de aparecer en el sitio público

#### Scenario: Carga de un archivo de media

- **WHEN** un editor autorizado carga una imagen o un video para una pieza
- **THEN** el sistema lo almacena y lo asocia a la pieza correspondiente

### Requirement: Gestión del alcance de consentimiento desde el panel

El panel DEBE (MUST) permitir consultar y modificar el `consent_scope` de cada pieza, y DEBE
mostrar de forma visible qué piezas están excluidas del índice del chatbot.

#### Scenario: Visualización del estado de consentimiento

- **WHEN** un editor consulta el listado de contenido de su tema
- **THEN** puede identificar el `consent_scope` de cada pieza sin abrir su detalle

#### Scenario: Modificación del alcance de consentimiento

- **WHEN** un editor autorizado cambia el `consent_scope` de una pieza
- **THEN** el sistema aplica el cambio y sincroniza el índice del chatbot en consecuencia

### Requirement: Registro de auditoría de acciones administrativas

El sistema DEBE (MUST) registrar, por cada creación, modificación, publicación, retiro o
eliminación de contenido, la cuenta que la ejecutó y la marca de tiempo.

#### Scenario: Trazabilidad de una modificación

- **WHEN** un administrador consulta el historial de una pieza de contenido
- **THEN** ve qué cuenta realizó cada acción y cuándo
