import pandas as pd
import re


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


def buscar_asignatura(df_maestro, nombre_asignatura):
    """
    Devuelve la fila correspondiente a una asignatura.

    Si el nombre de la asignatura aparece varias veces en el excel
    maestro (distintos grupos/cursos del mismo profesor), se devuelve
    la primera fila, PERO se avisa si las distintas filas tienen
    porcentajes distintos entre sí, ya que en ese caso escoger la
    primera podría no ser correcto (habría que desambiguar por curso
    o profesor).
    """

    coincidencias = []

    for _, fila in df_maestro.iterrows():

        materia = str(fila["MATERIA"]).strip().lower()

        if materia == nombre_asignatura.strip().lower():
            coincidencias.append(fila)

    if not coincidencias:
        return None, False

    porcentajes_distintos = False

    if len(coincidencias) > 1:
        textos_porcentajes = {
            str(fila["PORCENTAJES"]).strip() for fila in coincidencias
        }
        porcentajes_distintos = len(textos_porcentajes) > 1

    return coincidencias[0], porcentajes_distintos


def _normalizar_clave(nombre):
    """
    Normaliza el nombre de un item evaluativo tal y como aparece en
    el excel maestro, para poder reconocer variantes como:

        "PA+TO"   -> "PA+TO"
        "PA Y TO" -> "PA+TO"
        "PA + TO" -> "PA+TO"
        "PARCIAL" -> "PARCIAL 1"   (cuando la materia solo tiene un parcial)
    """

    clave = nombre.strip().upper()
    clave = re.sub(r"\s+Y\s+", "+", clave)
    clave = re.sub(r"\s*\+\s*", "+", clave)
    clave = re.sub(r"\s+", " ", clave)

    if clave == "PARCIAL":
        clave = "PARCIAL 1"

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

    pares = re.findall(r"([^:]+):\s*([\d]+)%", texto)

    for nombre, valor in pares:

        clave = _normalizar_clave(nombre)

        porcentajes[clave] = int(valor)

    return porcentajes
