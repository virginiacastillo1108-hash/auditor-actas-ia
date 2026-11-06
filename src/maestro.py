import re
import unicodedata
from difflib import SequenceMatcher

import pandas as pd


def cargar_maestro(ruta_excel):
    """
    Lee el Excel maestro de ESIC.
    """

    df = pd.read_excel(ruta_excel)

    # Eliminar columnas vacías
    df = df.dropna(axis=1, how="all")

    # Limpiar nombres de columnas
    df.columns = df.columns.astype(str).str.strip()

    return df


# =====================================================
# BÚSQUEDA DE LA ASIGNATURA EN EL MAESTRO
# =====================================================
#
# El nombre de la asignatura no siempre coincide letra por letra entre
# el acta y el maestro ("Human Resources Management" vs "Human Resources
# Management in a Digital Economy", tildes, "&" vs "and", un año añadido
# al final...). Además, la MISMA asignatura aparece varias veces en el
# maestro (una por curso/grupo/profesor) y con porcentajes distintos.
# Por eso no se busca solo por nombre: se puntúa cada fila del maestro
# con el parecido del nombre, del curso/grupo y del profesor.

PALABRAS_VACIAS = {
    "de", "la", "el", "los", "las", "y", "e", "en", "a", "i", "del",
    "and", "in", "the", "of", "for", "to", "para", "un", "una",
}

# Peso de cada criterio en la puntuación final
PESO_NOMBRE = 2.0
PESO_CURSO = 2.0
PESO_PROFESOR = 1.0

UMBRAL_NOMBRE = 0.72


def _sin_tildes(texto):

    t = unicodedata.normalize("NFKD", str(texto))

    return "".join(c for c in t if not unicodedata.combining(c))


def _palabras(texto):
    """Palabras 'significativas' del nombre de una asignatura (sin tildes, sin plurales ni palabras vacías)."""

    t = _sin_tildes(texto).lower().replace("&", " and ")
    t = re.sub(r"[^a-z0-9]+", " ", t)

    palabras = []

    for p in t.split():
        if p in PALABRAS_VACIAS:
            continue
        if len(p) > 3 and p.endswith("s"):
            p = p[:-1]
        palabras.append(p)

    return palabras


def similitud_nombres(a, b):
    """Parecido (0-1) entre dos nombres de asignatura, tolerante a tildes, plurales y palabras de relleno."""

    pa, pb = _palabras(a), _palabras(b)

    if not pa or not pb:
        return 0.0

    ratio = SequenceMatcher(None, " ".join(pa), " ".join(pb)).ratio()
    comunes = len(set(pa) & set(pb)) / len(set(pa) | set(pb))

    return max(ratio, comunes)


def _info_curso(texto):
    """Extrae año, titulaciones (GRMK, GRDB...) y grupos (A, B...) de textos como '3A GRMK + PAHD' o '3 GRMKT A y B'."""

    t = _sin_tildes(texto).upper()

    anio = re.search(r"\d", t)
    t = re.sub(r"(\d)([A-Z])", r"\1 \2", t)
    tokens = re.findall(r"[A-Z]+", t)

    grupos = {x for x in tokens if len(x) == 1 and x != "Y"}
    titulaciones = {x for x in tokens if len(x) >= 3 and x not in {"GRUPO", "AND"}}

    return (anio.group() if anio else None), titulaciones, grupos


def _titulaciones_coinciden(a, b):

    for x in a:
        for y in b:
            if x == y or x.startswith(y) or y.startswith(x):
                return True

    return False


def _puntuacion_curso(cursos_acta, curso_maestro):
    """0-1: coincidencia de año, titulación y grupo entre el curso del acta y el del maestro."""

    anio_m, tit_m, grupos_m = _info_curso(curso_maestro)

    mejor = 0.0

    for curso in cursos_acta:

        anio_a, tit_a, grupos_a = _info_curso(curso)

        puntos = 0.0

        if anio_a and anio_a == anio_m:
            puntos += 0.25

        if _titulaciones_coinciden(tit_a, tit_m):
            puntos += 0.5

        if not grupos_a or not grupos_m or (grupos_a & grupos_m):
            puntos += 0.25

        mejor = max(mejor, puntos)

    return mejor


def _puntuacion_profesor(nombre_archivo, profesor_maestro):
    """0-1: qué parte del nombre del profesor del maestro aparece en el nombre del archivo del acta."""

    if not nombre_archivo or not profesor_maestro or str(profesor_maestro) == "nan":
        return 0.0

    archivo = set(re.findall(r"[a-z0-9]+", _sin_tildes(nombre_archivo).lower()))

    mejor = 0.0

    for profesor in re.split(r"[/;,]", str(profesor_maestro)):

        partes = [
            p for p in re.findall(r"[a-z0-9]+", _sin_tildes(profesor).lower().replace("'", ""))
            if len(p) >= 3
        ]

        if not partes:
            continue

        mejor = max(mejor, sum(p in archivo for p in partes) / len(partes))

    return mejor


def buscar_asignatura(df_maestro, nombres_acta, cursos_acta=(), nombre_archivo=""):
    """
    Busca en el maestro la fila que corresponde al acta.

    Devuelve un diccionario con:
        fila            -> la fila elegida (o None si no hay ninguna parecida)
        puntuacion      -> puntuación de la fila elegida
        ambiguo         -> True si hay otras filas igual de buenas pero con
                           porcentajes DISTINTOS (hay que revisarlo a mano)
        alternativas    -> esas otras filas (lista de textos legibles)
        sugerencias     -> si no se ha encontrado, los nombres más parecidos
    """

    if isinstance(nombres_acta, str):
        nombres_acta = [nombres_acta]

    cursos_acta = [c for c in cursos_acta if c]

    puntuadas = []

    for _, fila in df_maestro.iterrows():

        materia = str(fila.get("MATERIA", "")).strip()

        if not materia or materia.lower() == "nan":
            continue

        similitud = max(similitud_nombres(n, materia) for n in nombres_acta)

        puntuadas.append((similitud, fila))

    if not puntuadas:
        return {"fila": None, "sugerencias": []}

    mejor_nombre = max(s for s, _ in puntuadas)

    if mejor_nombre < UMBRAL_NOMBRE:

        vistos = []

        for s, fila in sorted(puntuadas, key=lambda x: -x[0]):
            materia = str(fila["MATERIA"]).strip()
            if materia not in vistos:
                vistos.append(materia)
            if len(vistos) == 3:
                break

        return {"fila": None, "sugerencias": vistos}

    candidatas = []

    for similitud, fila in puntuadas:

        if similitud < UMBRAL_NOMBRE:
            continue

        total = (
            PESO_NOMBRE * similitud
            + PESO_CURSO * _puntuacion_curso(cursos_acta, str(fila.get("CURS", "")))
            + PESO_PROFESOR * _puntuacion_profesor(nombre_archivo, fila.get("PROFESSOR/A", ""))
        )

        candidatas.append((total, fila))

    candidatas.sort(key=lambda x: -x[0])

    mejor_puntuacion, mejor_fila = candidatas[0]
    porcentajes_elegidos = obtener_porcentajes(mejor_fila)

    alternativas = []

    for total, fila in candidatas[1:]:

        if mejor_puntuacion - total > 0.15:
            continue

        if obtener_porcentajes(fila) != porcentajes_elegidos:
            alternativas.append(descripcion_fila(fila))

    return {
        "fila": mejor_fila,
        "puntuacion": mejor_puntuacion,
        "ambiguo": bool(alternativas),
        "alternativas": alternativas,
    }


def descripcion_fila(fila):
    """Texto corto que identifica una fila del maestro (para mostrarlo en el informe)."""

    profesor = str(fila.get("PROFESSOR/A", "")).strip()
    curso = str(fila.get("CURS", "")).strip()

    return (
        f"{str(fila['MATERIA']).strip()} - {curso}"
        + (f" - {profesor}" if profesor and profesor.lower() != "nan" else "")
    )


# =====================================================
# PORCENTAJES DEL MAESTRO
# =====================================================

def _normalizar_clave(nombre):
    """
    Normaliza el nombre de un item evaluativo tal y como aparece en
    el excel maestro, para poder reconocer variantes como:

        "PA+TO"   -> "PA+TO"
        "PA Y TO" -> "PA+TO"
        "PA + TO" -> "PA+TO"
        "PARCIAL" -> "PARCIAL 1"   (cuando la materia solo tiene un parcial)
    """

    clave = _sin_tildes(nombre).strip().upper()
    clave = re.sub(r"\s+Y\s+", "+", clave)
    clave = re.sub(r"\s*\+\s*", "+", clave)
    clave = re.sub(r"\s+", " ", clave)

    # Erratas habituales en el maestro
    clave = clave.replace("PARICAL", "PARCIAL").replace("PARCAIL", "PARCIAL")

    # Abreviaturas y variantes: "P1", "1ER PARCIAL", "PARCIAL I", "EXAMEN"...
    clave = clave.strip(" .:-")
    clave = re.sub(r"^(\d)\s*(?:ER|O|º|°)?\s+PARCIAL$", r"PARCIAL \1", clave)
    clave = re.sub(r"^(?:P|PARCIAL|PARC\.?)\s*(\d)\s*(?:º|°)?$", r"PARCIAL \1", clave)
    clave = re.sub(r"^PARCIAL\s+II$", "PARCIAL 2", clave)
    clave = re.sub(r"^PARCIAL\s+I$", "PARCIAL 1", clave)

    alias = {
        "EXAMEN": "FINAL",
        "EXAMEN FINAL": "FINAL",
        "EXAM": "FINAL",
        "PARTICIPACION ACTIVA": "PA",
        "PARTICIPACION": "PA",
        "TRABAJO OBLIGATORIO": "TO",
        "TREBALL OBLIGATORI": "TO",
    }
    clave = alias.get(clave, clave)

    if clave == "PARCIAL":
        clave = "PARCIAL 1"

    # "TO+PA" y "PA+TO" son lo mismo: se ordenan las partes
    if "+" in clave:
        clave = "+".join(sorted(p.strip() for p in clave.split("+")))

    return clave


def obtener_porcentajes(fila_maestro):
    """
    Convierte el texto de la columna PORCENTAJES en un diccionario.

    Soporta tanto claves simples ("PARCIAL 1: 25%") como combinadas
    ("PA+TO: 40%", "PA Y TO: 80%"), que se devuelven tal cual bajo su
    clave combinada normalizada (p.ej. "PA+TO"), para que sea la capa
    de comparación (auditor.py) la que decida cómo repartir/agrupar
    ese valor combinado frente a las columnas del acta.
    """

    texto = str(fila_maestro["PORCENTAJES"])

    porcentajes = {}

    # Algunas filas olvidan los dos puntos ("TO 40%"): se añaden
    texto = re.sub(
        r"\b(TO|PA|FINAL|EXAMEN|P1|P2)\s+(\d)", r"\1: \2", texto, flags=re.IGNORECASE
    )

    # El símbolo % es opcional: algunas filas del maestro lo olvidan ("FINAL: 60")
    pares = re.findall(r"([^:]+):\s*(\d+(?:[.,]\d+)?)\s*%?", texto)

    for nombre, valor in pares:

        clave = _normalizar_clave(nombre)

        numero = float(valor.replace(",", "."))

        porcentajes[clave] = int(numero) if numero.is_integer() else numero

    return porcentajes
