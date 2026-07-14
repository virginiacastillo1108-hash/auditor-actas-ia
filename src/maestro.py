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
    """

    for _, fila in df_maestro.iterrows():

        materia = str(fila["MATERIA"]).strip().lower()

        if materia == nombre_asignatura.strip().lower():

            return fila

    return None


def obtener_porcentajes(fila_maestro):
    """
    Convierte el texto de la columna PORCENTAJES
    en un diccionario.
    """

    texto = str(fila_maestro["PORCENTAJES"])

    porcentajes = {}

    pares = re.findall(r"([^:]+):\s*([\d]+)%", texto)

    for nombre, valor in pares:

        porcentajes[nombre.strip().upper()] = int(valor)

    return porcentajes