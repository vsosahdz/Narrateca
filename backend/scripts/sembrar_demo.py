"""Contenido de demostración para desarrollo.

**No es material del archivo.** Son textos ilustrativos, genéricos y escritos
para este propósito, que sirven para ver la plataforma con forma antes de que
exista el archivo real. Se eliminan con `docker compose down -v`.

    NARRATECA_ADMIN_PASSWORD='...' python scripts/sembrar_demo.py

Toda pieza creada aquí lleva `source_ref` con prefijo `demo://`, de modo que sea
trivial distinguirla —y borrarla— cuando entre material verdadero.
"""

import asyncio
import os
import struct
import sys
import zlib
from pathlib import Path

import httpx

API = os.environ.get("NARRATECA_API", "http://localhost:8000/api/v1")

# Las credenciales vienen del entorno. Escribirlas aquí las versionaría, y una
# contraseña en el repositorio acaba reutilizada en algún lugar donde sí importa.
CREDENCIALES = {
    "email": os.environ.get("NARRATECA_ADMIN_EMAIL", "admin@tec.mx"),
    "password": os.environ.get("NARRATECA_ADMIN_PASSWORD", ""),
}

#: Acentos de cada comunidad, para que las imágenes de relleno se vean
#: coherentes con la paleta del sitio.
ACENTOS = {
    "migrantes": (140, 74, 31),
    "lgbtq": (90, 62, 155),
    "mujeres-discapacidad": (16, 96, 92),
    "mujeres-violencia": (150, 35, 74),
}


def png_degradado(rgb: tuple[int, int, int], ancho: int = 960, alto: int = 720) -> bytes:
    """PNG de un degradado sólido, como marcador visual de fotografía.

    Se genera aquí en lugar de usar una imagen de banco: un rectángulo de color
    se lee de inmediato como marcador de posición, mientras que una fotografía
    de archivo se confundiría con material real del proyecto.
    """
    r, g, b = rgb
    filas = []
    for y in range(alto):
        t = y / max(alto - 1, 1)
        # De la versión oscura a la clara del acento.
        pr = int(r * (0.55 + 0.45 * t))
        pg = int(g * (0.55 + 0.45 * t))
        pb = int(b * (0.55 + 0.45 * t))
        filas.append(b"\x00" + bytes([pr, pg, pb]) * ancho)

    def bloque(tipo: bytes, datos: bytes) -> bytes:
        cuerpo = tipo + datos
        return struct.pack(">I", len(datos)) + cuerpo + struct.pack(">I", zlib.crc32(cuerpo))

    ihdr = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + bloque(b"IHDR", ihdr)
        + bloque(b"IDAT", zlib.compress(b"".join(filas), 6))
        + bloque(b"IEND", b"")
    )


# --- Contenido ilustrativo --------------------------------------------------

PIEZAS: list[dict] = [
    # --- Migrantes ---------------------------------------------------------
    dict(
        theme_slug="migrantes", type="testimony", slug="las-primeras-noches",
        title="Las primeras noches en el camino",
        summary="Sobre el miedo, el insomnio y la compañía durante el tránsito.",
        body=(
            "Las primeras noches nadie duerme. Cada ruido en la oscuridad parece "
            "una linterna, un motor, una voz que pregunta.\n\n"
            "Lo que sostiene no es la valentía: es que alguien más esté despierto "
            "al mismo tiempo, y que al amanecer los dos sigan ahí.\n\n"
            "Después uno aprende a dormir por turnos. Eso también es una forma de "
            "cuidarse entre desconocidos."
        ),
        attribution="pseudonym", pseudonym="Ana", consent_scope="public",
        recorded_on="2024-03-11", foto=True,
        alt_text="Degradado en tonos ocres, marcador de fotografía pendiente.",
    ),
    dict(
        theme_slug="migrantes", type="interview", slug="coordinar-un-albergue",
        title="Coordinar un albergue en la frontera norte",
        summary="Conversación sobre lo que se necesita cuando llega una familia completa.",
        body=(
            "Entrevistadora · ¿Qué es lo primero que piden al llegar?\n\n"
            "Coordinadora · Un teléfono. Antes que comida, antes que una cama. "
            "Llevan días sin poder avisar que siguen vivos.\n\n"
            "Entrevistadora · ¿Cuántas personas atienden al mes?\n\n"
            "Coordinadora · Entre trescientas y cuatrocientas, y varía mucho con "
            "la temporada y con lo que pasa del otro lado.\n\n"
            "Entrevistadora · ¿Qué les hace falta?\n\n"
            "Coordinadora · Espacio para las familias. Los albergues se diseñaron "
            "pensando en hombres solos, y hoy llegan familias completas."
        ),
        attribution="named", person_name="Rosa Martínez",
        consent_scope="public", recorded_on="2024-05-02",
    ),
    dict(
        theme_slug="migrantes", type="photo", slug="la-fila-del-telefono",
        title="La fila del teléfono",
        summary="Al caer la tarde se forma la fila más larga del albergue.",
        attribution="anonymous", consent_scope="site_only", foto=True,
        alt_text=(
            "Degradado en tonos ocres que sustituye a una fotografía pendiente de "
            "cargar por el equipo de investigación."
        ),
    ),
    dict(
        theme_slug="migrantes", type="news_post", slug="presentacion-del-archivo-2025",
        title="El archivo se presenta en el campus",
        summary="El equipo compartió los primeros resultados con estudiantes y organizaciones.",
        body=(
            "La sesión reunió a estudiantes, organizaciones civiles y personas "
            "que participaron en la documentación.\n\n"
            "El archivo continúa abierto a nuevas colaboraciones."
        ),
        attribution="named", person_name="Equipo NarraTECa", consent_scope="site_only",
    ),
    dict(
        theme_slug="migrantes", type="curated_link", slug="reportaje-transito-migratorio",
        title="Un archivo testimonial documenta el tránsito migratorio en el noreste",
        summary=(
            "Reportaje sobre el trabajo del equipo de investigación y las voces que "
            "ha reunido durante los últimos dos años."
        ),
        source_name="Medio de ejemplo",
        external_url="https://ejemplo.mx/reportaje-archivo-testimonial",
        attribution="named", person_name="Redacción", consent_scope="site_only",
    ),
    # --- Comunidad LGBTQ+ --------------------------------------------------
    dict(
        theme_slug="lgbtq", type="testimony", slug="volver-al-pueblo",
        title="Volver al pueblo",
        summary="Sobre regresar a casa después de años fuera.",
        body=(
            "Volví con un discurso preparado. Lo había ensayado durante el "
            "camino, frase por frase.\n\n"
            "No alcancé a decir nada. Mi mamá me abrazó en la puerta y me dijo "
            "que la comida se enfriaba.\n\n"
            "Del pueblo me fui por miedo. Al pueblo regresé por lo mismo, y me "
            "encontré con otra cosa."
        ),
        attribution="anonymous", consent_scope="public", recorded_on="2023-11-18",
    ),
    dict(
        theme_slug="lgbtq", type="interview", slug="organizar-la-primera-marcha",
        title="Organizar la primera marcha en una ciudad pequeña",
        summary="Sobre convocar cuando nadie sabe si irá alguien.",
        body=(
            "Entrevistador · ¿Cuánta gente esperaban?\n\n"
            "Organizadora · Veinte. Éramos siete organizando y pensábamos que "
            "quizá llegarían veinte.\n\n"
            "Entrevistador · ¿Cuántas llegaron?\n\n"
            "Organizadora · Cerca de trescientas. Lo que más recuerdo no es el "
            "número: es que mucha gente llegó sola, sin conocer a nadie."
        ),
        attribution="pseudonym", pseudonym="Dani", consent_scope="public",
    ),
    dict(
        theme_slug="lgbtq", type="photo", slug="la-plaza-esa-tarde",
        title="La plaza esa tarde",
        summary="El punto de reunión antes de salir.",
        attribution="anonymous", consent_scope="site_only", foto=True,
        alt_text="Degradado en tonos violeta, marcador de fotografía pendiente.",
    ),
    # --- Mujeres con discapacidad -------------------------------------------
    dict(
        theme_slug="mujeres-discapacidad", type="testimony", slug="la-rampa-que-no-existia",
        title="La rampa que no existía",
        summary="Sobre estudiar en un campus que no fue pensado para una.",
        body=(
            "Me tomó dos años y once oficios conseguir una rampa. No una rampa "
            "nueva: la que ya estaba en los planos desde antes de que yo entrara.\n\n"
            "Durante ese tiempo entré por la puerta de servicio, junto a los "
            "contenedores de basura. Aprendí los horarios de recolección mejor "
            "que mi horario de clases.\n\n"
            "Cuando la pusieron, nadie avisó. Un lunes simplemente estaba ahí."
        ),
        attribution="pseudonym", pseudonym="Lucía", consent_scope="public",
        recorded_on="2024-02-06",
    ),
    dict(
        theme_slug="mujeres-discapacidad", type="interview", slug="el-diagnostico-tardio",
        title="Sobre el diagnóstico tardío",
        summary="Conversación acerca de los años previos a tener un nombre para lo que pasaba.",
        body=(
            "Entrevistadora · ¿Cuánto tiempo pasó hasta el diagnóstico?\n\n"
            "Participante · Diecinueve años. Durante casi todos me dijeron que "
            "exageraba.\n\n"
            "Entrevistadora · ¿Qué cambió al tenerlo?\n\n"
            "Participante · Nada en mi cuerpo. Todo en cómo me escuchan. La misma "
            "frase, dicha antes y después del papel, pesa distinto."
        ),
        attribution="anonymous", consent_scope="public",
    ),
    dict(
        theme_slug="mujeres-discapacidad", type="photo", slug="la-entrada-de-servicio",
        title="La entrada de servicio",
        summary="Durante dos años, la única accesible.",
        attribution="anonymous", consent_scope="site_only", foto=True,
        alt_text="Degradado en tonos verde azulado, marcador de fotografía pendiente.",
    ),
    # --- Mujeres y violencia de género --------------------------------------
    dict(
        theme_slug="mujeres-violencia", type="testimony", slug="el-dia-que-me-creyeron",
        title="El día que me creyeron",
        summary="Sobre la primera vez que alguien no pidió pruebas.",
        body=(
            "La trabajadora social no me preguntó qué había hecho yo. No me "
            "preguntó por qué no me había ido antes, ni por qué había vuelto.\n\n"
            "Solo me dijo: te creo. Y luego: ¿qué necesitas hoy?\n\n"
            "Llevaba cuatro años explicándome. Ese día no tuve que explicar nada."
        ),
        attribution="anonymous", consent_scope="no_ai", sensitivity="high",
        recorded_on="2024-06-20",
    ),
    dict(
        theme_slug="mujeres-violencia", type="interview", slug="acompanar-procesos",
        title="Acompañar procesos legales",
        summary="Conversación con quien acompaña a mujeres en denuncias.",
        body=(
            "Entrevistadora · ¿Qué es lo más difícil del acompañamiento?\n\n"
            "Acompañante · Que el proceso pide contar la historia una y otra vez, "
            "a personas distintas, en lugares distintos. Cada vez es volver.\n\n"
            "Entrevistadora · ¿Qué ayuda?\n\n"
            "Acompañante · Que alguien vaya con ella. Literalmente: que camine al "
            "lado y esté ahí cuando salga."
        ),
        attribution="pseudonym", pseudonym="Marta", consent_scope="public",
    ),
    dict(
        theme_slug="mujeres-violencia", type="news_post", slug="taller-de-documentacion",
        title="Taller de documentación con organizaciones locales",
        summary="Sesión de trabajo sobre registro y resguardo de testimonios.",
        body="El taller reunió a seis organizaciones de la zona metropolitana.",
        attribution="named", person_name="Equipo NarraTECa", consent_scope="site_only",
    ),
]

EQUIPO = [
    dict(
        full_name="Dra. Rosa Martínez",
        role_title="Investigadora principal · Escuela de Humanidades y Educación",
        bio=(
            "Coordina el archivo testimonial y la línea de trabajo sobre migración "
            "en el noreste. Su investigación se centra en las formas de cuidado "
            "que surgen durante el tránsito."
        ),
        position=1,
    ),
    dict(
        full_name="Mtro. Julián Ortega",
        role_title="Investigador asociado · Documentación audiovisual",
        bio=(
            "Responsable del registro audiovisual del archivo y de los criterios "
            "de accesibilidad del material. Trabaja en subtitulado y en las "
            "condiciones de consentimiento para el uso del testimonio."
        ),
        position=2,
    ),
    dict(
        full_name="Dra. Ximena Cruz",
        role_title="Investigadora · Estudios de género",
        bio=(
            "Acompaña las líneas de mujeres con discapacidad y de violencia de "
            "género. Trabaja en metodologías de entrevista que no obliguen a "
            "repetir el relato."
        ),
        position=3,
    ),
    dict(
        full_name="Lic. Andrés Villa",
        role_title="Asistente de investigación",
        bio=(
            "Apoya la catalogación del archivo y la preparación del material para "
            "su publicación en la plataforma."
        ),
        position=4,
    ),
]


async def main() -> int:
    if not CREDENCIALES["password"]:
        print(
            "Falta la contraseña de la cuenta de administración.\n"
            "  NARRATECA_ADMIN_PASSWORD='...' python scripts/sembrar_demo.py",
            file=sys.stderr,
        )
        return 1

    async with httpx.AsyncClient(timeout=60) as c:
        sesion = await c.post(f"{API}/admin/login", json=CREDENCIALES)
        if sesion.status_code != 200:
            print("No fue posible iniciar sesión. ¿Existe la cuenta de administración?")
            print("  python -m app.cli crear-admin --email admin@tec.mx --nombre Admin")
            return 1

        creadas = omitidas = 0

        for pieza in PIEZAS:
            datos = {k: v for k, v in pieza.items() if k not in {"foto"}}
            datos["source_ref"] = f"demo://{pieza['theme_slug']}/{pieza['slug']}"

            if pieza.get("foto"):
                imagen = png_degradado(ACENTOS[pieza["theme_slug"]])
                subida = await c.post(
                    f"{API}/admin/media",
                    data={
                        "theme_slug": pieza["theme_slug"],
                        "sensitivity": pieza.get("sensitivity", "normal"),
                    },
                    files={"file": (f"{pieza['slug']}.png", imagen, "image/png")},
                )
                if subida.status_code == 201:
                    datos["media_key"] = subida.json()["media_key"]
                    datos["media_mime"] = subida.json()["media_mime"]

            creada = await c.post(f"{API}/admin/content", json=datos)
            if creada.status_code == 409:
                omitidas += 1
                continue
            if creada.status_code != 201:
                print(f"  ✗ {pieza['slug']}: {creada.status_code} {creada.text[:110]}")
                continue

            publicada = await c.post(f"{API}/admin/content/{creada.json()['id']}/publish")
            marca = "✓" if publicada.status_code == 200 else "✗"
            print(f"  {marca} {pieza['theme_slug']:22} {pieza['slug']}")
            creadas += 1

        # El equipo no tiene clave natural como `source_ref`, así que la
        # idempotencia se resuelve aquí: sin esto, cada ejecución duplicaría a
        # las mismas personas.
        existentes = {m["full_name"] for m in (await c.get(f"{API}/admin/team")).json()}
        for integrante in EQUIPO:
            if integrante["full_name"] in existentes:
                continue
            respuesta = await c.post(f"{API}/admin/team", json=integrante)
            if respuesta.status_code == 201:
                print(f"  ✓ equipo                 {integrante['full_name']}")

        print(f"\n{creadas} piezas creadas · {omitidas} ya existían")
        print("Contenido de DEMOSTRACIÓN. Se elimina con: docker compose down -v")
        return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(asyncio.run(main()))
