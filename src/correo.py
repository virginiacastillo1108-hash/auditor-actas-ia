"""
Generación del correo (informal) que se envía al profesor cuando su
acta tiene algo que corregir.

Reglas de redacción pedidas:
- Tono normal, no muy formal.
- Si hay notas sin redondear a 1 decimal, NO se listan una a una: se
  avisa de forma genérica de que hay que redondear a 1 decimal.
- El resto de incidencias (notas incorrectas, NP, forzados a 4,
  asistencia, DX, 2ª convocatoria...) sí se detallan alumno a alumno.
- Siempre se cierra pidiendo que corrija el excel y lo reenvíe, y
  recordando que no puede subir notas al Campus Virtual hasta recibir
  el ok definitivo.
"""


def _hay_redondeo(resultado_notas, resultado_notas_dx, resultado_notas_recu):

    if resultado_notas.get("errores_redondeo"):
        return True

    if resultado_notas_dx and resultado_notas_dx.get("errores_redondeo"):
        return True

    if resultado_notas_recu and resultado_notas_recu.get("errores_redondeo"):
        return True

    return False


def hay_algo_que_corregir(
    errores_porcentajes,
    resultado_notas,
    tiene_dx=False,
    resultado_notas_dx=None,
    errores_porcentajes_recu=None,
    resultado_notas_recu=None,
):
    """
    Indica si hay algún motivo para escribir al profesor. Si todo está
    correcto, no tiene sentido generar correo.
    """

    if errores_porcentajes:
        return True

    if resultado_notas.get("errores_nota") or resultado_notas.get("errores_np"):
        return True

    if resultado_notas.get("forzados_a_4") or resultado_notas.get("avisos_asistencia"):
        return True

    if _hay_redondeo(resultado_notas, resultado_notas_dx, resultado_notas_recu):
        return True

    if tiene_dx and resultado_notas_dx and any(resultado_notas_dx.values()):
        return True

    if errores_porcentajes_recu:
        return True

    if resultado_notas_recu and not resultado_notas_recu.get("acta_solo_1a_convocatoria"):
        if (
            resultado_notas_recu.get("faltan_recu")
            or resultado_notas_recu.get("errores_nota")
            or resultado_notas_recu.get("errores_np")
        ):
            return True

    return False


def generar_correo_profesor(
    asignatura,
    curso,
    errores_porcentajes,
    resultado_notas,
    tiene_dx=False,
    resultado_notas_dx=None,
    errores_porcentajes_recu=None,
    resultado_notas_recu=None,
    nombre_profesor="",
):
    """
    Genera el asunto y el cuerpo de un correo informal para el
    profesor con los puntos a corregir. Devuelve (asunto, cuerpo), o
    (None, None) si no hay nada que corregir.
    """

    if not hay_algo_que_corregir(
        errores_porcentajes, resultado_notas, tiene_dx, resultado_notas_dx,
        errores_porcentajes_recu, resultado_notas_recu,
    ):
        return None, None

    saludo = "Hola" + (f" {nombre_profesor}" if nombre_profesor else "") + ","

    lineas = [
        saludo,
        "",
        f"Hemos revisado el acta de {asignatura} ({curso}) y hay algunos puntos "
        "que necesitamos que nos revises antes de darle el visto bueno:",
        "",
    ]

    punto = 1

    # 1. Ponderaciones (1ª convocatoria)
    if errores_porcentajes:
        lineas.append(
            f"{punto}. Los % de evaluación puestos en el excel no coinciden con "
            "los de la guía docente:"
        )
        for e in errores_porcentajes:
            lineas.append(f"   - {e['campo']}: debería ser {e['maestro']}% y tienes puesto {e['acta']}%")
        lineas.append("")
        punto += 1

    # 2. Redondeo (genérico, SIN listar alumno a alumno)
    if _hay_redondeo(resultado_notas, resultado_notas_dx, resultado_notas_recu):
        lineas.append(
            f"{punto}. Hay varias notas finales puestas con más de 1 decimal "
            "(por ejemplo 8.875 en vez de 8.9). Recuerda que las notas finales "
            "solo pueden llevar 1 decimal: repasa el excel entero y redondea "
            "las que falten."
        )
        lineas.append("")
        punto += 1

    # 3. Notas incorrectas (1ª convocatoria)
    if resultado_notas.get("errores_nota"):
        lineas.append(
            f"{punto}. Estas notas finales no coinciden con el cálculo según "
            "los % de la asignatura:"
        )
        for e in resultado_notas["errores_nota"]:
            lineas.append(f"   - {e['Alumno']}: tienes puesto {e['Nota profesor']}, debería ser {e['Nota SIVAA']}")
        lineas.append("")
        punto += 1

    # 4. NP
    if resultado_notas.get("errores_np"):
        lineas.append(
            f"{punto}. Revisa el NP (no presentado) de estos alumnos:"
        )
        for e in resultado_notas["errores_np"]:
            if e["Tipo"] == "np_incumplida":
                lineas.append(f"   - {e['Alumno']}: debería figurar como NP y tienes puesto {e['Valor profesor']}")
            else:
                lineas.append(
                    f"   - {e['Alumno']}: tienes puesto NP pero según los datos "
                    f"debería tener nota calculable ({e['Nota SIVAA']}), revísalo"
                )
        lineas.append("")
        punto += 1

    # 5. Forzados a 4 (para que lo confirme)
    if resultado_notas.get("forzados_a_4"):
        lineas.append(
            f"{punto}. Estos alumnos deben tener la nota forzada a un 4 según "
            "la normativa (examen final y/o TO suspendidos); confirma que lo "
            "tienes así en el excel:"
        )
        for e in resultado_notas["forzados_a_4"]:
            lineas.append(f"   - {e['Alumno']}: {e['Motivo']}")
        lineas.append("")
        punto += 1

    # 6. Asistencia
    if resultado_notas.get("avisos_asistencia"):
        lineas.append(
            f"{punto}. Estos alumnos superan el 15% de faltas, así que su nota "
            "final solo debe contar la ponderación del examen final; confirma "
            "que está bien calculado:"
        )
        for e in resultado_notas["avisos_asistencia"]:
            lineas.append(f"   - {e['Alumno']}: {e['Faltas %']}% de faltas")
        lineas.append("")
        punto += 1

    # 7. DX
    if tiene_dx and resultado_notas_dx and any(resultado_notas_dx.values()):
        lineas.append(f"{punto}. En la sección de alumnos DX también hay algo que revisar:")
        for e in resultado_notas_dx.get("errores_nota", []):
            lineas.append(f"   - {e['Alumno']}: tienes puesto {e['Nota profesor']}, debería ser {e['Nota SIVAA']}")
        for e in resultado_notas_dx.get("errores_np", []):
            lineas.append(f"   - {e['Alumno']}: revisa el NP")
        if resultado_notas_dx.get("errores_redondeo"):
            lineas.append("   - Alguna nota de esta sección también tiene más de 1 decimal, redondéala.")
        for e in resultado_notas_dx.get("forzados_a_4", []):
            lineas.append(f"   - {e['Alumno']}: nota forzada a un 4 ({e['Motivo']}), confírmalo")
        lineas.append("")
        punto += 1

    # 8. % de la 2ª convocatoria
    if errores_porcentajes_recu:
        lineas.append(
            f"{punto}. Los % de la 2ª convocatoria no coinciden con los de "
            "evaluación continua (deben ser los mismos):"
        )
        for e in errores_porcentajes_recu:
            lineas.append(f"   - {e['campo']}: debería ser {e['maestro']}% y tienes puesto {e['acta']}%")
        lineas.append("")
        punto += 1

    # 9. 2ª convocatoria: pendientes, notas, NP
    if resultado_notas_recu and not resultado_notas_recu.get("acta_solo_1a_convocatoria"):

        if resultado_notas_recu.get("faltan_recu"):
            lineas.append(
                f"{punto}. Estos alumnos debían presentarse a la recuperación y "
                "todavía no tienen nada puesto en la 2ª convocatoria:"
            )
            for e in resultado_notas_recu["faltan_recu"]:
                lineas.append(f"   - {e['Alumno']}: le falta {e['Falta']}")
            lineas.append("")
            punto += 1

        if resultado_notas_recu.get("errores_nota"):
            lineas.append(f"{punto}. Estas notas de la 2ª convocatoria no coinciden con el cálculo:")
            for e in resultado_notas_recu["errores_nota"]:
                lineas.append(f"   - {e['Alumno']}: tienes puesto {e['Nota profesor']}, debería ser {e['Nota SIVAA']}")
            lineas.append("")
            punto += 1

        if resultado_notas_recu.get("errores_np"):
            lineas.append(f"{punto}. Revisa también el NP de estos alumnos en la 2ª convocatoria:")
            for e in resultado_notas_recu["errores_np"]:
                lineas.append(f"   - {e['Alumno']}")
            lineas.append("")
            punto += 1

    lineas.append(
        "Cuando lo tengas corregido, nos lo vuelves a enviar y le echamos otro "
        "vistazo."
    )
    lineas.append("")
    lineas.append(
        "Recuerda que hasta que no os demos el ok definitivo, no podéis subir "
        "las notas finales al Campus Virtual."
    )
    lineas.append("")
    lineas.append("¡Gracias!")
    lineas.append("Un saludo")

    asunto = f"Revisión acta {asignatura} ({curso}) - cambios pendientes"
    cuerpo = "\n".join(lineas)

    return asunto, cuerpo
