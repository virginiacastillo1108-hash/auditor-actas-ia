import pandas as pd


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

    # -----------------------------------------
    # INFORMACIÓN GENERAL
    # -----------------------------------------

    def obtener_asignatura(self):

        return str(self.info.iloc[1, 0]).strip()

    def obtener_curso(self):

        return str(self.info.iloc[0, 0]).strip()

    # -----------------------------------------
    # PONDERACIONES DEL ACTA
    # -----------------------------------------

    def obtener_ponderaciones(self):

        fila = self.notas.iloc[0]

        ponderaciones = {}

        for columna, valor in zip(self.notas.columns, fila):

            ponderaciones[str(columna).strip()] = valor

        return ponderaciones

    # -----------------------------------------
    # ALUMNOS
    # -----------------------------------------

    def obtener_alumnos(self):
        """
        Devuelve solo las filas de alumnos reales.

        Algunas actas incluyen, debajo de la lista principal,
        una segunda tabla con alumnos con adaptaciones (p.ej.
        "ALUMNES DX") que tiene su propia cabecera y sus propios
        porcentajes. Esa segunda tabla NO tiene nada en la columna
        NOMBRE en su primera fila (ahí aparece el título de la
        sección, en la columna APELLIDOS), así que se usa eso como
        marca de fin de la lista de alumnos: en cuanto aparece una
        fila sin NOMBRE, se corta ahí.
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
                # Fin de la tabla de alumnos (empieza otra sección,
                # o son filas vacías de relleno)
                break

            filas_validas.append(fila)

        alumnos = pd.DataFrame(filas_validas, columns=self.notas.columns)

        alumnos.reset_index(drop=True, inplace=True)

        return alumnos
