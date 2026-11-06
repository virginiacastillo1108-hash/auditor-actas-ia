import io
import os
import re
import unicodedata

import numpy as np
import openpyxl
import pandas as pd

from calculadora import a_porcentaje_entero, leer_faltas


# =====================================================
# UTILIDADES
# =====================================================

def normalizar(texto):
    """Mayúsculas, sin tildes y con espacios simples: 'Participación ' -> 'PARTICIPACION'."""

    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().upper()


def _es_vacio(valor):

    if valor is None:
        return True

    try:
        if pd.isna(valor):
            return True
    except (TypeError, ValueError):
        pass

    return str(valor).strip().upper() in ("", "NAN", "NONE")


def _es_texto(valor):
    return isinstance(valor, str) and valor.strip() != ""


def _leer_bytes(origen):
    """Acepta una ruta o un archivo subido (Streamlit) y devuelve sus bytes."""

    if isinstance(origen, (str, os.PathLike)):
        with open(origen, "rb") as f:
            return f.read()

    if hasattr(origen, "seek"):
        origen.seek(0)

    return origen.read()


def _nombre_de_archivo(origen):

    if isinstance(origen, (str, os.PathLike)):
        return os.path.basename(str(origen))

    return getattr(origen, "name", "") or ""


# =====================================================
# RECONOCIMIENTO DE COLUMNAS
# =====================================================

def concepto_de_columna(texto):
    """
    Dice a qué concepto corresponde la cabecera de una columna, sin
    depender de que esté escrita exactamente igual en todas las actas:

        "EXAMEN FINAL/1 CONVO"                 -> examen
        "TREBALL OBLIGAT/participacion activa" -> to
        "Participacion activa" / "PARTICIPA ACTIVA" -> pa
        "NOTA FINAL (SIN RECU) 1 CONVO"        -> nota_final
        "NOTA FINAL 2 CONV"                    -> nota_final_2
    """

    t = normalizar(texto)

    if t.startswith("NOTA FINAL"):
        return "nota_final_2" if "2 CONV" in t else "nota_final"

    if t.startswith("EXAMEN RECU"):
        return "examen_recu"

    if t.startswith("EXAMEN"):
        return "examen"

    if t.startswith(("TREBALL", "TRABAJO", "TRABALL")):
        return "to_recu" if "RECU" in t else "to"

    if t.startswith("PARTICIPA"):
        return "pa"

    if t.startswith("PARCIAL 2"):
        return "parcial2"

    if t.startswith("PARCIAL 1") or t == "PARCIAL":
        return "parcial1"

    if t.startswith("FALTAS"):
        return "faltas"

    return None


CONCEPTOS = [
    "parcial1", "parcial2", "examen", "to", "pa", "faltas",
    "nota_final", "examen_recu", "to_recu", "nota_final_2",
]

# concepto interno -> nombre "de maestro" usado para comparar porcentajes
NOMBRE_PCT = {
    "parcial1": "PARCIAL 1",
    "parcial2": "PARCIAL 2",
    "examen": "FINAL",
    "to": "TO",
    "pa": "PA",
    "examen_recu": "EXAMEN RECU",
    "to_recu": "TREBALL RECU",
}


def _resolver_columnas(nombres):
    """{concepto: nombre_real_de_columna}; None si el acta no tiene esa columna."""

    columnas = {c: None for c in CONCEPTOS}

    for nombre in nombres:
        concepto = concepto_de_columna(nombre)
        if concepto and columnas[concepto] is None:
            columnas[concepto] = nombre

    return columnas


def _nombres_unicos(cabeceras):
    """Convierte la fila de cabecera en nombres de columna únicos y legibles."""

    vistos = {}
    nombres = []

    for i, valor in enumerate(cabeceras):

        nombre = str(valor).strip() if _es_texto(valor) else f"col_{i}"

        if normalizar(nombre) == "NOMBRE":
            nombre = "NOMBRE"
        elif normalizar(nombre) == "APELLIDOS":
            nombre = "APELLIDOS"

        if nombre in vistos:
            vistos[nombre] += 1
            nombre = f"{nombre} ({vistos[nombre]})"
        else:
            vistos[nombre] = 1

        nombres.append(nombre)

    return nombres


# =====================================================
# ACTA
# =====================================================

class Acta:

    def __init__(self, ruta_excel, nombre_archivo=None):

        self.nombre_archivo = nombre_archivo or _nombre_de_archivo(ruta_excel)

        datos = _leer_bytes(ruta_excel)
        libro = openpyxl.load_workbook(io.BytesIO(datos), data_only=True)
        hoja = self._elegir_hoja(libro)

        filas = list(hoja.iter_rows())
        valores = [[c.value for c in fila] for fila in filas]
        self._formatos = [[c.number_format for c in fila] for fila in filas]

        # Hoja completa tal cual está en el Excel (fila Excel = índice + 1)
        self.info = pd.DataFrame(valores).astype(object)
        self.info = self.info.where(self.info.notna(), np.nan)

        self.fila_cabecera = self._localizar_cabecera()
        self.fila_porcentajes = self._localizar_porcentajes()
        self.fila_cabecera_dx = self._localizar_cabecera_dx()

        cabeceras = self.info.iloc[self.fila_cabecera].tolist()
        self.nombres_columna = _nombres_unicos(cabeceras)
        self.columnas = _resolver_columnas(self.nombres_columna)

        self.notas = self._construir_tabla(
            self.fila_porcentajes + 1,
            self.fila_cabecera_dx if self.fila_cabecera_dx is not None else len(self.info),
            self.nombres_columna,
            self.columnas,
        )

        # En algunas actas (p.ej. Human Resources) la columna del trabajo
        # lleva también la participación ("TREBALL OBLIGAT/participacion
        # activa") y la columna de participación está vacía: entonces la
        # nota de esa columna cuenta para TO + PA a la vez.
        col_to = self.columnas["to"]
        col_pa = self.columnas["pa"]

        self.to_incluye_pa = bool(
            col_to
            and "PARTICIPA" in normalizar(col_to)
            and (
                col_pa is None
                or self.notas[col_pa].apply(_es_vacio).all()
            )
        )

    # -----------------------------------------
    # LOCALIZACIÓN DE LAS PARTES DEL ACTA
    # -----------------------------------------

    @staticmethod
    def _elegir_hoja(libro):

        for nombre in libro.sheetnames:
            if nombre.strip().lower() == "notes":
                return libro[nombre]

        for nombre in libro.sheetnames:
            for fila in libro[nombre].iter_rows(max_row=30, values_only=True):
                if any(
                    isinstance(v, str) and normalizar(v).startswith("EXAMEN FINAL")
                    for v in fila
                ):
                    return libro[nombre]

        return libro[libro.sheetnames[0]]

    def _textos_normalizados(self, indice_fila):

        return [
            normalizar(v) for v in self.info.iloc[indice_fila].tolist() if _es_texto(v)
        ]

    def _localizar_cabecera(self):
        """Fila con las cabeceras de la tabla principal (EXAMEN FINAL + NOMBRE/APELLIDOS)."""

        for i in range(len(self.info)):
            textos = self._textos_normalizados(i)

            tiene_examen = any(t.startswith("EXAMEN FINAL") for t in textos)
            tiene_nombre = any(t in ("NOMBRE", "APELLIDOS") for t in textos)

            if tiene_examen and tiene_nombre:
                return i

        raise ValueError(
            "No he encontrado la fila de cabeceras del acta (la que tiene "
            "APELLIDOS / NOMBRE / EXAMEN FINAL). Revisa que el Excel tiene "
            "el formato habitual de acta."
        )

    def _localizar_porcentajes(self):
        """Fila con los % de evaluación: la primera tras la cabecera con valores entre 0 y 1."""

        posiciones = [
            i for i, n in enumerate(self.info.iloc[self.fila_cabecera].tolist())
            if _es_texto(n) and concepto_de_columna(n) in NOMBRE_PCT
        ]

        for i in range(self.fila_cabecera + 1, min(self.fila_cabecera + 5, len(self.info))):

            fila = self.info.iloc[i].tolist()
            numericos = [
                fila[p] for p in posiciones
                if p < len(fila) and isinstance(fila[p], (int, float)) and not pd.isna(fila[p])
            ]

            if len(numericos) >= 2 and all(0 <= v <= 1.0001 for v in numericos):
                return i

        return self.fila_cabecera + 1

    def _localizar_cabecera_dx(self):
        """
        La sección de alumnos con adaptación (DX) repite una cabecera con
        PARCIAL 1 / EXAMEN FINAL más abajo. Puede venir con un título
        "ALUMNES DX" encima o con el título en la misma fila (p.ej.
        "25-26/A-DX"), por eso se busca la cabecera repetida y no el título.
        """

        for i in range(self.fila_porcentajes + 1, len(self.info)):
            textos = self._textos_normalizados(i)

            if any(t.startswith("EXAMEN FINAL") for t in textos) and any(
                t.startswith("PARCIAL") for t in textos
            ):
                return i

        return None

    # -----------------------------------------
    # TABLAS DE ALUMNOS
    # -----------------------------------------

    def _normalizar_faltas(self, fila, posicion):
        """Pasa las faltas a puntos de porcentaje (11.6 / 0.19 con formato % / '15.4%' -> 11.6 / 19 / 15.4)."""

        valor = self.info.iat[fila, posicion]
        formato = ""

        try:
            formato = self._formatos[fila][posicion] or ""
        except IndexError:
            pass

        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            if pd.isna(valor):
                return np.nan
            return float(valor) * 100 if "%" in formato else float(valor)

        leido = leer_faltas(valor)

        return np.nan if leido is None else leido

    def _construir_tabla(self, desde, hasta, nombres, columnas):

        posicion_nombre = nombres.index("NOMBRE") if "NOMBRE" in nombres else None
        posicion_apellidos = nombres.index("APELLIDOS") if "APELLIDOS" in nombres else None
        posicion_faltas = nombres.index(columnas["faltas"]) if columnas.get("faltas") else None

        filas = []

        for i in range(desde, hasta):

            fila = self.info.iloc[i].tolist()

            nombre = fila[posicion_nombre] if posicion_nombre is not None else None
            apellidos = fila[posicion_apellidos] if posicion_apellidos is not None else None

            hay_nombre = not _es_vacio(nombre)
            hay_apellidos = (
                not _es_vacio(apellidos)
                and "DX" not in normalizar(apellidos).split()
                and "ALUMNES" not in normalizar(apellidos)
            )

            if not (hay_nombre or hay_apellidos):
                continue

            fila = (fila + [np.nan] * len(nombres))[: len(nombres)]

            if posicion_faltas is not None:
                fila[posicion_faltas] = self._normalizar_faltas(i, posicion_faltas)

            filas.append(fila + [i + 1])

        tabla = pd.DataFrame(filas, columns=nombres + ["__fila"])

        return tabla.reset_index(drop=True)

    # -----------------------------------------
    # INFORMACIÓN GENERAL
    # -----------------------------------------

    def _filas_de_titulo(self):
        """Textos de las filas por encima de la cabecera (una lista por fila con texto)."""

        filas = []

        for i in range(self.fila_cabecera):
            textos = [
                str(v).strip() for v in self.info.iloc[i].tolist() if _es_texto(v)
            ]
            if textos:
                filas.append(textos)

        return filas

    @staticmethod
    def _limpiar_titulo(texto):
        """Quita el curso académico ('2025-2026') que algunos profesores añaden al nombre."""

        texto = re.sub(r"\b20\d{2}\s*[-/]\s*(20)?\d{2}\b", "", texto)

        return re.sub(r"\s+", " ", texto).strip(" -–·,.")

    def candidatos_asignatura(self):
        """Posibles nombres de la asignatura (la fila justo encima de la cabecera puede traer varios)."""

        filas = self._filas_de_titulo()

        if not filas:
            raise ValueError("No encuentro el nombre de la asignatura en el acta.")

        candidatos = []

        for texto in filas[-1]:
            limpio = self._limpiar_titulo(texto)
            if limpio and limpio not in candidatos:
                candidatos.append(limpio)

        return candidatos

    def candidatos_curso(self):

        filas = self._filas_de_titulo()

        if len(filas) < 2:
            return []

        candidatos = []

        for texto in filas[-2]:
            limpio = self._limpiar_titulo(texto)
            if limpio and limpio not in candidatos:
                candidatos.append(limpio)

        return candidatos

    def obtener_asignatura(self):

        return self.candidatos_asignatura()[0]

    def obtener_curso(self):

        candidatos = self.candidatos_curso()

        return candidatos[0] if candidatos else ""

    # -----------------------------------------
    # PONDERACIONES
    # -----------------------------------------

    def _ponderaciones(self, fila_porcentajes, nombres_cabecera, columnas):
        """{'PARCIAL 1': 30, 'FINAL': 60, ...} en tanto por cien, por concepto y no por nombre de columna."""

        fila = self.info.iloc[fila_porcentajes].tolist()
        fila = (fila + [np.nan] * len(nombres_cabecera))[: len(nombres_cabecera)]

        ponderaciones = {}

        for concepto, nombre_pct in NOMBRE_PCT.items():

            nombre_columna = columnas.get(concepto)

            if nombre_columna is None:
                ponderaciones[nombre_pct] = 0
                continue

            ponderaciones[nombre_pct] = a_porcentaje_entero(
                fila[nombres_cabecera.index(nombre_columna)]
            )

        return ponderaciones

    def obtener_ponderaciones(self):

        return self._ponderaciones(
            self.fila_porcentajes, self.nombres_columna, self.columnas
        )

    # -----------------------------------------
    # ALUMNOS (tabla principal)
    # -----------------------------------------

    def obtener_alumnos(self):

        return self.notas

    # -----------------------------------------
    # SECCIÓN DX (alumnos con adaptaciones)
    # -----------------------------------------

    def tiene_seccion_dx(self):

        return self.fila_cabecera_dx is not None

    def obtener_dx(self):
        """
        Devuelve (alumnos_dx, ponderaciones_dx, columnas_dx). La sección DX
        tiene su propia cabecera (con nombres que pueden variar respecto a la
        tabla principal), así que sus columnas se resuelven por separado.
        """

        if self.fila_cabecera_dx is None:
            return pd.DataFrame(), {}, {}

        cabecera = self.info.iloc[self.fila_cabecera_dx].tolist()
        fila_pct = self.info.iloc[self.fila_cabecera_dx + 1].tolist()

        # APELLIDOS / NOMBRE vienen en la fila de los porcentajes (o en la propia cabecera)
        for posicion, valor in enumerate(fila_pct):
            if (
                posicion < len(cabecera)
                and _es_texto(valor)
                and normalizar(valor) in ("NOMBRE", "APELLIDOS")
                and not _es_texto(cabecera[posicion])
            ):
                cabecera[posicion] = valor

        nombres = _nombres_unicos(cabecera)
        columnas = _resolver_columnas(nombres)

        alumnos = self._construir_tabla(
            self.fila_cabecera_dx + 2, len(self.info), nombres, columnas
        )

        ponderaciones = self._ponderaciones(self.fila_cabecera_dx + 1, nombres, columnas)

        return alumnos, ponderaciones, columnas
