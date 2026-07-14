import os


def generar_informe(
    asignatura,
    curso,
    total_alumnos,
    errores_porcentajes,
    errores_notas,
    no_evaluables,
):
    """
    Construye el texto del informe final de auditoría.
    """

    lineas = []

    lineas.append("=" * 60)
    lineas.append("INFORME DE AUDITORÍA - SIVAA")
    lineas.append("=" * 60)
    lineas.append(f"Asignatura: {asignatura}")
    lineas.append(f"Curso: {curso}")
    lineas.append(f"Total de alumnos detectados: {total_alumnos}")
    lineas.append("")

    # --- Ponderaciones ---
    lineas.append("-" * 60)
    lineas.append("1. PONDERACIONES (acta vs excel maestro)")
    lineas.append("-" * 60)

    if not errores_porcentajes:
        lineas.append("✅ Las ponderaciones del acta coinciden con el excel maestro.")
    else:
        lineas.append(
            f"❌ Se han encontrado {len(errores_porcentajes)} discrepancia(s) "
            "en las ponderaciones:"
        )
        for error in errores_porcentajes:
            lineas.append(
                f"   - {error['campo']}: maestro = {error['maestro']}%  "
                f"|  acta = {error['acta']}%"
            )

    lineas.append("")

    # --- Notas ---
    lineas.append("-" * 60)
    lineas.append("2. NOTAS FINALES")
    lineas.append("-" * 60)

    if not errores_notas:
        lineas.append(
            "✅ Todas las notas comprobables coinciden con el cálculo de SIVAA."
        )
    else:
        lineas.append(f"❌ {len(errores_notas)} nota(s) no coinciden con SIVAA:")
        for error in errores_notas:
            lineas.append(
                f"   - {error['Alumno']}: profesor = {error['Nota profesor']}  "
                f"|  SIVAA = {error['Nota SIVAA']}"
            )

    lineas.append("")

    # --- No evaluables ---
    if no_evaluables:
        lineas.append("-" * 60)
        lineas.append("3. NOTAS NO EVALUABLES AUTOMÁTICAMENTE")
        lineas.append("-" * 60)
        lineas.append(
            f"⚠️  {len(no_evaluables)} nota(s) no se han podido interpretar de "
            "forma automática (revisar manualmente):"
        )
        for item in no_evaluables:
            lineas.append(
                f"   - {item['Alumno']}: valor original = {item['Valor original']!r}"
                f"  (SIVAA calcula = {item['Nota SIVAA']})"
            )
        lineas.append("")

    return "\n".join(lineas)


def guardar_informe(informe, ruta_salida):
    """
    Guarda el texto del informe en disco, creando la carpeta
    de destino si no existe.
    """

    carpeta = os.path.dirname(ruta_salida)

    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(informe)
