import pandas as pd


# Nombres "base" de columna que pueden venir con variantes según el
# acta (p.ej. con o sin el sufijo "1 CONVO"). Se busca por prefijo.
PREFIJOS_COLUMNA = {
    "parcial1": "PARCIAL 1",
    "parcial2": "PARCIAL 2",
    "examen": "EXAMEN FINAL",
    "to": "TREBALL OBLIGAT",
    "pa": "PARTICIPA ACTIVA",
    "faltas": "FALTAS",
    "nota_final": "NOTA FINAL (SIN RECU)",
    "examen_recu": "EXAMEN RECU",
    "to_recu": "TREBALL RECU",
    "nota_final_2": "NOTA FINAL 2 CONV",
}


def _resolver_columnas(columnas_df):
    """
    Dado el listado de columnas reales de una tabla (main o DX),
    devuelve un diccionario {concepto: nombre_real_de_columna},
    buscando por prefijo para admitir variantes como:

        "NOTA FINAL (SIN RECU)"           (acta 1)
        "NOTA FINAL (SIN RECU) 1 CONVO"   (actas 2 y 3)
    """

    columnas = {}

    for concepto, prefijo in PREFIJOS_COLUMNA.items():

        encontrada = None

        for columna in columnas_df:

            texto = str(columna).strip()

            if texto.upper().startswith(prefijo.upper()):
                encontrada = texto
                break

        columnas[concepto] = encontrada

    return columnas


class Acta:

    def __init__(self, ruta_excel):

        self.ruta_excel = ruta_excel

        self.info = pd.read_excel(
            ruta_excel,
            sheet_name="Notes",
            header=None
        )

        self.notas = pd.read_excel(
            ruta_excel,
            sheet_name="Notes",
            header=2
        )

        self.columnas = _resolver_columnas(self.notas.columns)

    # -----------------------------------------
    # INFORMACIÓN GENERAL
    # -----------------------------------------

    def obtener_asignatura(self):

        return str(self.info.iloc[1, 0]).strip()

    def obtener_curso(self):

        return str(self.info.iloc[0, 0]).strip()

    # -----------------------------------------
    # PONDERACIONES DEL ACTA (tabla principal)
    # -----------------------------------------

    def obtener_ponderaciones(self):

        fila = self.notas.iloc[0]

        ponderaciones = {}

        for columna, valor in zip(self.notas.columns, fila):

            ponderaciones[str(columna).strip()] = valor

        return ponderaciones

    # -----------------------------------------
    # ALUMNOS (tabla principal)
    # -----------------------------------------

    def obtener_alumnos(self):
        """
        Devuelve solo las filas de alumnos reales de la tabla
        principal (antes de la sección "ALUMNES DX", si la hay).
        """

        candidatos = self.notas.iloc[2:].copy()

        filas_validas = []

        for _, fila in candidatos.iterrows():

            nombre = fila.get("NOMBRE")

            nombre_valido = (
                nombre is not None
                and not (isinstance(nombre, float) and pd.isna(nombre))
                and str(nombre).strip() != ""
                and str(nombre).strip().upper() != "NAN"
            )

            if not nombre_valido:
                break

            filas_validas.append(fila)

        alumnos = pd.DataFrame(filas_validas, columns=self.notas.columns)

        alumnos.reset_index(drop=True, inplace=True)

        return alumnos

    # -----------------------------------------
    # SECCIÓN DX (alumnos con adaptaciones)
    # -----------------------------------------

    def _localizar_bloque_dx(self):
        """
        Busca en la hoja completa (self.info, sin recortar cabecera)
        la fila donde empieza la sección "ALUMNES DX". Devuelve el
        índice de esa fila, o None si el acta no tiene esta sección.
        """

        for idx, valor in enumerate(self.info.iloc[:, 0]):

            texto = str(valor).strip().upper()

            if "ALUMNES DX" in texto or texto == "DX":
                return idx

        return None

    def tiene_seccion_dx(self):

        return self._localizar_bloque_dx() is not None

    def obtener_ponderaciones_dx(self):
        """
        La sección DX repite la misma estructura que la tabla
        principal: una fila de título ("ALUMNES DX"), una fila de
        cabeceras y una fila de porcentajes. Devuelve el diccionario
        de ponderaciones de esa fila, con las mismas claves de
        columna que la tabla principal.
        """

        idx_titulo = self._localizar_bloque_dx()

        if idx_titulo is None:
            return {}

        fila_cabecera = self.info.iloc[idx_titulo + 1]
        fila_porcentajes = self.info.iloc[idx_titulo + 2]

        ponderaciones = {}

        for columna, valor in zip(fila_cabecera, fila_porcentajes):

            if columna is None or (isinstance(columna, float) and pd.isna(columna)):
                continue

            ponderaciones[str(columna).strip()] = valor

        return ponderaciones

    def obtener_alumnos_dx(self):
        """
        Devuelve el DataFrame de alumnos de la sección DX (puede
        estar vacío si el acta no tiene alumnos con adaptaciones).

        OJO con la cabecera de esta sección: en la práctica viene
        repartida en dos filas: la fila "idx_titulo+1" trae los
        nombres de los conceptos (PARCIAL 1, EXAMEN FINAL...) pero
        dejando en blanco las dos primeras columnas, y es la fila
        "idx_titulo+2" (la misma que trae los % ) la que realmente
        pone "APELLIDOS"/"NOMBRE" en esas dos primeras columnas. Hay
        que combinar ambas filas para tener la cabecera completa.
        """

        idx_titulo = self._localizar_bloque_dx()

        if idx_titulo is None:
            return pd.DataFrame()

        fila_cabecera = self.info.iloc[idx_titulo + 1]
        fila_porcentajes = self.info.iloc[idx_titulo + 2]

        columnas = []

        for valor_cab, valor_perc in zip(fila_cabecera, fila_porcentajes):

            cab_vacia = valor_cab is None or (
                isinstance(valor_cab, float) and pd.isna(valor_cab)
            ) or str(valor_cab).strip() == ""

            if not cab_vacia:
                columnas.append(str(valor_cab).strip())
            elif isinstance(valor_perc, str) and valor_perc.strip() != "":
                columnas.append(valor_perc.strip())
            else:
                columnas.append(f"col_{len(columnas)}")

        inicio_alumnos = idx_titulo + 3

        filas_validas = []

        for idx in range(inicio_alumnos, len(self.info)):

            fila = self.info.iloc[idx]

            # La columna NOMBRE de la sección DX es la segunda
            nombre = fila.iloc[1] if len(fila) > 1 else None

            nombre_valido = (
                nombre is not None
                and not (isinstance(nombre, float) and pd.isna(nombre))
                and str(nombre).strip() != ""
                and str(nombre).strip().upper() != "NAN"
            )

            if not nombre_valido:
                break

            filas_validas.append(fila.tolist())

        if not filas_validas:
            return pd.DataFrame(columns=columnas)

        alumnos = pd.DataFrame(filas_validas, columns=columnas[: len(filas_validas[0])])

        return alumnos
