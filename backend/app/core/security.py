"""Hashing de contraseñas.

Se usa Argon2id, ganador del Password Hashing Competition y recomendación actual
de OWASP. Es una función de derivación de clave deliberadamente costosa en tiempo
y en memoria, lo que encarece los ataques por fuerza bruta con hardware
especializado de una forma que las funciones basadas solo en CPU no logran.

Nunca se almacena la contraseña en claro ni cifrada de forma reversible: solo el
hash, que no permite recuperar el original (spec `admin-cms`).
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Parámetros por defecto de argon2-cffi, alineados con las recomendaciones de
# OWASP. Subirlos endurece el sistema a costa de latencia en el inicio de sesión.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Devuelve el hash Argon2id de una contraseña."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contraseña contra su hash.

    Devuelve `False` ante cualquier fallo en lugar de propagar la excepción: al
    llamador solo le interesa si coincide, y distinguir entre "no coincide" y
    "el hash está corrupto" filtraría información al exterior.
    """
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Indica si el hash usa parámetros antiguos y conviene regenerarlo.

    Permite endurecer los parámetros con el tiempo y migrar las contraseñas
    existentes de forma transparente, en el siguiente inicio de sesión de cada
    persona.
    """
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True
