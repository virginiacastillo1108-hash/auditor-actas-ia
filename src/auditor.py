from calculadora import comparar_nota


def comprobar_porcentajes(porcentajes_acta, porcentajes_maestro):

    errores = []

    equivalencias = {
        "PARCIAL 1": "PARCIAL 1",
        "PARCIAL 2": "PARCIAL 2",
        "FINAL": "EXAMEN FINAL/1 CONVO",
        "TO": "TREBALL OBLIGAT",
        "PA": "PARTICIPA ACTIVA"
    }

    for maestro, acta in equivalencias.items():

        valor_maestro = porcentajes_maestro.get(maestro, 0)

        valor_acta = porcentajes_acta.get(acta, 0)

        valor_acta = round(float(valor_acta) * 100)

        if valor_maestro != valor_acta:

            errores.append({
                "campo": maestro,
                "maestro": valor_maestro,
                "acta": valor_acta
            })

    return errores


def auditar_notas(df_alumnos, porcentajes_maestro):
    """
    Recorre a los alumnos y compara la nota calculada por SIVAA
    con la nota puesta por el profesor.

    Devuelve dos listas:
    - errores: alumnos cuya nota no coincide con el cálculo de SIVAA
    - no_evaluables: alumnos cuya nota original no se ha podido
      interpretar automáticamente (por ejemplo texto no reconocido)
      y que conviene revisar a mano
    """

    errores = []
    no_evaluables = []

    for _, alumno in df_alumnos.iterrows():

        nombre = str(alumno.get("NOMBRE", "")).strip()
        apellidos = str(alumno.get("APELLIDOS", "")).strip()

        if apellidos.lower() == "nan":
            apellidos = ""

        nombre_completo = f"{apellidos} {nombre}".strip()

        resultado = comparar_nota(alumno, porcentajes_maestro)

        if not resultado["evaluable"]:
            no_evaluables.append({
                "Alumno": nombre_completo,
                "Valor original": resultado["nota_profesor_original"],
                "Nota SIVAA": resultado["nota_sivaa"],
            })
            continue

        if not resultado["correcto"]:

            errores.append({

                "Alumno": nombre_completo,

                "Nota profesor":
                    resultado["nota_profesor"],

                "Nota SIVAA":
                    resultado["nota_sivaa"]

            })

    return errores, no_evaluables
