import os


def _seccion_lista(lineas, titulo, items, formateador, vacio_ok="✅ Todo correcto."):

    lineas.append("-" * 60)
    lineas.append(titulo)
    lineas.append("-" * 60)

    if not items:
        lineas.append(vacio_ok)
    else:
        for item in items:
            lineas.append(formateador(item))

    lineas.append("")


def generar_informe(
    asignatura,
    curso,
    total_alumnos,
    errores_porcentajes,
    resultado_notas,
    resultado_notas_dx=None,
    tiene_dx=False,
    errores_porcentajes_recu=None,
    resultado_notas_recu=None,
):
    """
    Construye el texto del informe final de auditoría.

    `resultado_notas` es el diccionario devuelto por
    auditor.auditar_notas (errores_nota, errores_np,
    errores_redondeo, no_evaluables, avisos_asistencia,
    forzados_a_4).
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

    # --- Notas incorrectas ---
    _seccion_lista(
        lineas,
        "2. NOTAS FINALES INCORRECTAS",
        resultado_notas["errores_nota"],
        lambda e: (
            f"   ❌ {e['Alumno']}: profesor = {e['Nota profesor']}  "
            f"|  SIVAA = {e['Nota SIVAA']}"
        ),
    )

    # --- Errores de NP ---
    def _formato_np(e):
        if e["Tipo"] == "np_incumplida":
            return (
                f"   ❌ {e['Alumno']}: debería figurar como NP (examen o TO no "
                f"presentado) y en su lugar tiene: {e['Valor profesor']!r}"
            )
        return (
            f"   ⚠️  {e['Alumno']}: el profesor ha puesto NP pero, según los "
            f"datos del examen/TO, sí debería tener nota calculable "
            f"(SIVAA = {e['Nota SIVAA']})"
        )

    _seccion_lista(
        lineas,
        "3. NOTAS QUE DEBERÍAN SER NP (o viceversa)",
        resultado_notas["errores_np"],
        _formato_np,
    )

    # --- Errores de redondeo ---
    _seccion_lista(
        lineas,
        "4. NOTAS SIN REDONDEAR A 1 DECIMAL",
        resultado_notas["errores_redondeo"],
        lambda e: (
            f"   ⚠️  {e['Alumno']}: nota puesta = {e['Nota profesor']}  "
            f"(debería redondearse a {e['Nota SIVAA']})"
        ),
    )

    # --- No evaluables ---
    _seccion_lista(
        lineas,
        "5. NOTAS NO EVALUABLES AUTOMÁTICAMENTE (revisar a mano)",
        resultado_notas["no_evaluables"],
        lambda e: (
            f"   ⚠️  {e['Alumno']}: valor original = {e['Valor original']!r}"
            f"  (SIVAA calcula = {e['Nota SIVAA']})"
        ),
        vacio_ok="✅ No hay casos pendientes de revisión manual.",
    )

    # --- Avisos informativos: asistencia y forzados a 4 ---
    lineas.append("-" * 60)
    lineas.append("6. AVISOS INFORMATIVOS")
    lineas.append("-" * 60)

    avisos_asistencia = resultado_notas["avisos_asistencia"]
    forzados = resultado_notas["forzados_a_4"]

    if avisos_asistencia:
        lineas.append(
            f"ℹ️  {len(avisos_asistencia)} alumno(s) con más del 15% de faltas "
            "(solo cuenta la ponderación del examen final):"
        )
        for e in avisos_asistencia:
            lineas.append(f"   - {e['Alumno']}: faltas = {e['Faltas %']}%")
        lineas.append("")

    if forzados:
        lineas.append(
            f"ℹ️  {len(forzados)} alumno(s) con la nota forzada a un 4 "
            "(examen final o TO suspendidos):"
        )
        for e in forzados:
            lineas.append(f"   - {e['Alumno']}: {e['Motivo']}")
        lineas.append("")

    if not avisos_asistencia and not forzados:
        lineas.append("Sin avisos.")
        lineas.append("")

    # --- Sección 2ª convocatoria ---
    lineas.append("=" * 60)
    lineas.append("7. SEGUNDA CONVOCATORIA (recuperación)")
    lineas.append("=" * 60)

    if errores_porcentajes_recu:
        lineas.append(
            f"❌ Se han encontrado {len(errores_porcentajes_recu)} discrepancia(s) "
            "en los % de la 2ª convocatoria (deben ser los mismos que en "
            "evaluación continua):"
        )
        for error in errores_porcentajes_recu:
            lineas.append(
                f"   - {error['campo']}: esperado = {error['maestro']}%  "
                f"|  acta = {error['acta']}%"
            )
        lineas.append("")
    else:
        lineas.append("✅ Los % de la 2ª convocatoria coinciden con los de evaluación continua.")
        lineas.append("")

    if resultado_notas_recu is None or resultado_notas_recu.get("acta_solo_1a_convocatoria"):
        lineas.append(
            "ℹ️  Este excel no tiene ningún dato en las columnas de 2ª convocatoria: "
            "se entiende que es un acta de solo 1ª convocatoria y no procede auditar la recuperación."
        )
        lineas.append("")
    elif not any(v for k, v in resultado_notas_recu.items() if k != "acta_solo_1a_convocatoria"):
        lineas.append("✅ Sin alumnos que debieran recuperar, o todo correcto en 2ª convocatoria.")
        lineas.append("")
    else:
        _seccion_lista(
            lineas, "7.1 Alumnos a los que les falta nota de recuperación",
            resultado_notas_recu["faltan_recu"],
            lambda e: f"   ❌ {e['Alumno']}: debía presentarse a recuperar {e['Falta']} y no tiene nada puesto.",
            vacio_ok="✅ Todos los que debían recuperar algo tienen nota puesta.",
        )
        _seccion_lista(
            lineas, "7.2 Notas de 2ª convocatoria incorrectas",
            resultado_notas_recu["errores_nota"],
            lambda e: f"   ❌ {e['Alumno']}: profesor = {e['Nota profesor']}  |  SIVAA = {e['Nota SIVAA']}",
        )
        _seccion_lista(
            lineas, "7.3 NP en 2ª convocatoria",
            resultado_notas_recu["errores_np"],
            _formato_np,
        )
        _seccion_lista(
            lineas, "7.4 Redondeo en 2ª convocatoria",
            resultado_notas_recu["errores_redondeo"],
            lambda e: f"   ⚠️  {e['Alumno']}: nota puesta = {e['Nota profesor']} (debería ser {e['Nota SIVAA']})",
        )
        if resultado_notas_recu["forzados_a_4"]:
            lineas.append("7.5 Avisos: nota de 2ª convocatoria forzada a un 4")
            for e in resultado_notas_recu["forzados_a_4"]:
                lineas.append(f"   - {e['Alumno']}: {e['Motivo']}")
            lineas.append("")

    # --- Sección DX ---
    if tiene_dx:
        lineas.append("=" * 60)
        lineas.append("8. ALUMNOS DX (adaptaciones)")
        lineas.append("=" * 60)

        if resultado_notas_dx is None:
            lineas.append("⚠️  El acta tiene sección DX pero no se ha podido leer/auditar.")
        elif not any(resultado_notas_dx.values()):
            lineas.append("✅ Sin alumnos DX o todo correcto en la sección DX.")
        else:
            _seccion_lista(
                lineas, "8.1 Notas incorrectas (DX)",
                resultado_notas_dx["errores_nota"],
                lambda e: f"   ❌ {e['Alumno']}: profesor = {e['Nota profesor']}  |  SIVAA = {e['Nota SIVAA']}",
            )
            _seccion_lista(
                lineas, "8.2 NP (DX)",
                resultado_notas_dx["errores_np"],
                _formato_np,
            )
            _seccion_lista(
                lineas, "8.3 Redondeo (DX)",
                resultado_notas_dx["errores_redondeo"],
                lambda e: f"   ⚠️  {e['Alumno']}: nota puesta = {e['Nota profesor']} (debería ser {e['Nota SIVAA']})",
            )
            if resultado_notas_dx["forzados_a_4"]:
                lineas.append("8.4 Avisos (DX): nota forzada a un 4")
                for e in resultado_notas_dx["forzados_a_4"]:
                    lineas.append(f"   - {e['Alumno']}: {e['Motivo']}")
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
