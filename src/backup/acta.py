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

        alumnos = self.notas.iloc[2:].copy()

        alumnos.reset_index(drop=True, inplace=True)

        return alumnos