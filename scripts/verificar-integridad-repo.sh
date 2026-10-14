#!/usr/bin/env bash
#
# Verifica que ningún archivo de código fuente esté siendo ignorado por git.
#
# Existe por un fallo concreto. Las reglas de `.gitignore` que protegen el
# material del archivo están escritas sin barra inicial, para que apliquen a
# cualquier profundidad:
#
#     archive/
#     media/
#     var/
#
# Esos también son nombres de módulos. El resultado fue que
# `backend/app/modules/archive/` y `backend/app/modules/media/` nunca llegaron
# al repositorio. En local todo funcionaba —los archivos estaban ahí— y git no
# dice nada de lo que ignora, así que el primer síntoma apareció tres envíos
# después, como `ModuleNotFoundError` en integración continua.
#
# El guion comprueba dos direcciones:
#
#   1. En una copia de trabajo: archivos de código presentes en el disco que
#      git está descartando. Es el caso que falló.
#   2. En integración continua, donde solo existe lo versionado: archivos ya
#      versionados que una regla nueva pasaría a ignorar. Es la regresión.
#
# Uso:  ./scripts/verificar-integridad-repo.sh

set -euo pipefail

cd "$(dirname "$0")/.."

# Dónde vive el código. Deliberadamente acotado: `backend/archivo` y
# `backend/var` contienen material y deben seguir ignorados.
RUTAS_DE_CODIGO=(backend/app backend/tests backend/alembic frontend/src infra)

# Sin `mapfile`: macOS trae bash 3.2 y no lo tiene. El guion debe correr igual
# en la máquina de quien desarrolla que en integración continua.
archivos=$(
  find "${RUTAS_DE_CODIGO[@]}" -type f \
    \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.css' -o -name '*.tf' \) \
    -not -path '*/__pycache__/*' -not -path '*/.terraform/*' \
    2>/dev/null | sort
)

if [ -z "$archivos" ]; then
  echo "✗ No se encontró ningún archivo de código. ¿Se ejecuta desde el repositorio?" >&2
  exit 1
fi

total=$(printf '%s\n' "$archivos" | wc -l | tr -d ' ')

# `--no-index` es lo que hace útil la comprobación. Sin esa opción,
# `check-ignore` calla ante cualquier archivo ya versionado, porque un archivo
# versionado no se ignora aunque una regla lo señale. Eso dejaría ver solo el
# caso del módulo nuevo y no la regresión: alguien añade una regla amplia, el
# código sigue en el repositorio por inercia y el fallo aparece el día que
# alguien clona de cero.
ignorados=$(printf '%s\n' "$archivos" | git check-ignore --stdin --verbose --no-index || true)

if [ -n "$ignorados" ]; then
  echo "✗ Hay código fuente que git está ignorando:" >&2
  echo >&2
  echo "$ignorados" | sed 's/^/    /' >&2
  echo >&2
  echo "  Cada línea muestra: archivo-de-reglas:línea:regla<TAB>archivo afectado." >&2
  echo "  Si la regla es necesaria, reincorpore el directorio con una negación" >&2
  echo "  (\`!ruta/al/modulo/\`). Git no readmite un archivo cuyo directorio" >&2
  echo "  padre está excluido, así que la negación debe apuntar a la carpeta." >&2
  exit 1
fi

echo "✓ $total archivos de código, ninguno ignorado."

# Segunda comprobación: el material del archivo debe seguir fuera. Una negación
# demasiado amplia podría abrir la puerta sin que nadie lo note, y el
# repositorio es público.
echo
echo "Comprobando que el material confidencial sigue ignorado:"
expuesto=0
for ruta in \
  archivo/migrantes/testimonio.docx \
  backend/archivo/lgbtq/entrevista.pdf \
  backend/var/media/public/foto.jpg \
  backend/var/media/sensitive/video.mp4 \
  frontend/public/testimonio.mp4; do
  if git check-ignore -q "$ruta"; then
    printf '    ✓ %s\n' "$ruta"
  else
    printf '    ✗ %s — NO está ignorado\n' "$ruta" >&2
    expuesto=1
  fi
done

if [ "$expuesto" -ne 0 ]; then
  echo >&2
  echo "✗ Una ruta de material del archivo dejó de estar protegida." >&2
  exit 1
fi

echo
echo "✓ Integridad del repositorio verificada."
