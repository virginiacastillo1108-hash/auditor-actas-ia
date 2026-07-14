import pandas as pd


def leer_excel(archivo_excel):
    """
    Lee un acta ESIC localizando automáticamente
    la fila donde empiezan los encabezados.
    """

    # Leer la hoja SIN encabezados
    df_temp = pd.read_excel(
        archivo_excel,
        header=None,
        sheet_name="Notes"
    )

    fila_encabezado = None

    # Buscar la fila donde aparecen APELLIDOS y NOMBRE
    for i in range(len(df_temp)):

        fila = df_temp.iloc[i].astype(str).str.upper()

        if "APELLIDOS" in fila.values and "NOMBRE" in fila.values:

            fila_encabezado = i
            break

    if fila_encabezado is None:
        raise Exception(
            "No se ha encontrado la fila de encabezados del acta."
        )

    # Leer otra vez usando esa fila como encabezado
    df = pd.read_excel(
        archivo_excel,
        sheet_name="Notes",
        header=fila_encabezado
    )

    # Eliminar filas completamente vacías
    df = df.dropna(how="all")

    # Eliminar columnas completamente vacías
    df = df.dropna(axis=1, how="all")

    # Limpiar nombres de columnas
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace("\n", " ", regex=False)
    )

    # Reiniciar índices
    df.reset_index(drop=True, inplace=True)

    print("\n========== COLUMNAS ==========")

    for columna in df.columns:
        print(repr(columna))

    print("==============================")

    return df