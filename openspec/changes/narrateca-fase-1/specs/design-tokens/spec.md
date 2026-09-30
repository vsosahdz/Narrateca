## ADDED Requirements

### Requirement: Paleta intercambiable desde código

El sistema DEBE (MUST) definir todos los colores de la interfaz mediante tokens declarados en
archivos de código. Ningún color DEBE aparecer escrito directamente en los componentes.

Sustituir la paleta completa DEBE lograrse editando los archivos de tokens, sin modificar
componentes.

#### Scenario: Cambio de la paleta completa

- **WHEN** se sustituyen los valores del archivo de tokens de color
- **THEN** toda la interfaz refleja la nueva paleta sin cambios en los componentes

#### Scenario: Ausencia de colores literales en componentes

- **WHEN** se audita el código de los componentes de interfaz
- **THEN** no existen valores de color escritos directamente; todos referencian tokens

### Requirement: Tokens base compartidos y acento por tema

El sistema DEBE (MUST) separar los tokens en dos capas: una base compartida por todo el sitio
—tipografía, espaciado, radios, superficies y colores de texto— y una capa de acento
definida por cada uno de los cuatro temas.

Los cuatro temas DEBEN compartir la capa base, de modo que el sitio se perciba como una
sola plataforma.

#### Scenario: Acento propio por tema

- **WHEN** una persona navega de una página temática a otra
- **THEN** el color de acento cambia según el tema
- **AND** la tipografía, el espaciado y las superficies permanecen iguales

#### Scenario: Alta del acento de un tema nuevo

- **WHEN** se registra un tema nuevo con su color de acento
- **THEN** sus páginas adoptan ese acento sin modificar la capa base ni los componentes

### Requirement: Contraste verificable de los tokens de color

Toda combinación de token de texto sobre token de superficie definida en el sistema DEBE (MUST)
alcanzar una relación de contraste de al menos 4.5 a 1 para texto normal y 3 a 1 para
texto grande y elementos de interfaz.

El proyecto DEBE incluir una verificación automatizable de estas relaciones.

#### Scenario: Verificación de la paleta

- **WHEN** se ejecuta la verificación de contraste sobre los tokens definidos
- **THEN** reporta cada combinación con su relación de contraste y señala las que no
  alcanzan el mínimo

#### Scenario: Acento temático que no alcanza el mínimo

- **WHEN** se define un color de acento cuyo contraste sobre la superficie base es inferior
  al mínimo
- **THEN** la verificación falla e identifica la combinación problemática
