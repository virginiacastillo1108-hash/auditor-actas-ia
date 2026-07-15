import math

from calculadora import comparar_nota, comparar_nota_segunda_convocatoria, esta_vacio


def _porcentaje(valor):
    """
    Convierte una celda de ponderación (fracción 0-1, p.ej. 0.25) a
    un entero en tanto por cien (25), tratando de forma segura los
    casos vacíos/NaN (que no son lo mismo que 0, pero para el cálculo
    de ponderaciones significan "no aplica" -> 0%).
    """

    if valor is None:
        return 0

    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return 0

    if math.isnan(numero):
        return 0

    return round(numero * 100)


# Columnas "conceptuales" del acta y su nombre real en el excel maestro
CONCEPTOS = ["PARCIAL 1", "PARCIAL 2", "FINAL", "TO", "PA"]

EQUIVALENCIAS_ACTA = {
    "PARCIAL 1": "PARCIAL 1",
    "PARCIAL 2": "PARCIAL 2",
    "FINAL": "EXAMEN FINAL/1 CONVO",
    "TO": "TREBALL OBLIGAT",
    "PA": "PARTICIPA ACTIVA",
}


def _valor_directo(porcentajes_maestro, concepto):
    return porcentajes_maestro.get(concepto)


def _buscar_clave_combinada(porcentajes_maestro, concepto):
    """
    Busca una clave combinada del excel maestro que contenga el
    concepto pedido, por ejemplo "PA+TO" contiene tanto "PA" como
    "TO". Devuelve (clave, valor) o (None, None).
    """

    for clave, valor in porcentajes_maestro.items():
        if "+" in clave and concepto in clave.split("+"):
            return clave, valor

    return None, None


def resolver_porcentajes_efectivos(porcentajes_maestro, ponderaciones_acta):
    """
    Construye el diccionario de porcentajes que se usará para CALCULAR
    la nota de cada alumno (PARCIAL 1, PARCIAL 2, FINAL, TO, PA en
    tanto por cien).

    Cuando el excel maestro da un porcentaje individual para el
    concepto, se usa ese. Cuando el maestro solo da un valor
    combinado (p.ej. "PA+TO: 40%"), no sabemos por sí solo cómo se
    reparte entre PA y TO: en ese caso se usa el reparto que el propio
    profesor ha puesto en el acta (que es la única fuente que lo
    especifica), y la comprobación de que el TOTAL combinado coincide
    con el maestro se hace aparte, en `comprobar_porcentajes`.
    """

    efectivos = {}

    for concepto in CONCEPTOS:

        valor = _valor_directo(porcentajes_maestro, concepto)

        if valor is not None:
            efectivos[concepto] = valor
            continue

        clave_combinada, _ = _buscar_clave_combinada(porcentajes_maestro, concepto)

        if clave_combinada is not None:
            columna_acta = EQUIVALENCIAS_ACTA[concepto]
            valor_acta = ponderaciones_acta.get(columna_acta, 0)
            efectivos[concepto] = _porcentaje(valor_acta)
        else:
            efectivos[concepto] = 0

    return efectivos


def comprobar_porcentajes(ponderaciones_acta, porcentajes_maestro):
    """
    Compara los % puestos en el acta contra los del excel maestro
    (o la guía docente). Soporta que el maestro dé los porcentajes de
    PA y TO por separado o combinados (p.ej. "PA+TO: 40%"), en cuyo
    caso se compara la SUMA de PA+TO del acta contra ese valor
    combinado, en vez de comparar cada uno por separado.
    """

    errores = []

    ya_comprobados = set()

    for concepto in CONCEPTOS:

        if concepto in ya_comprobados:
            continue

        columna_acta = EQUIVALENCIAS_ACTA[concepto]
        valor_acta = ponderaciones_acta.get(columna_acta, 0)
        valor_acta = _porcentaje(valor_acta)

        valor_directo = _valor_directo(porcentajes_maestro, concepto)

        if valor_directo is not None:
            if valor_directo != valor_acta:
                errores.append({
                    "campo": concepto,
                    "maestro": valor_directo,
                    "acta": valor_acta,
                })
            continue

        clave_combinada, valor_combinado = _buscar_clave_combinada(
            porcentajes_maestro, concepto
        )

        if clave_combinada is not None:
            conceptos_combinados = clave_combinada.split("+")
            suma_acta = 0
            for c in conceptos_combinados:
                col = EQUIVALENCIAS_ACTA.get(c)
                if col:
                    suma_acta += _porcentaje(ponderaciones_acta.get(col))
                    ya_comprobados.add(c)

            if suma_acta != valor_combinado:
                errores.append({
                    "campo": clave_combinada,
                    "maestro": valor_combinado,
                    "acta": suma_acta,
                })
            continue

        # El maestro no dice nada de este concepto (0% esperado)
        if valor_acta != 0:
            errores.append({
                "campo": concepto,
                "maestro": 0,
                "acta": valor_acta,
            })

    return errores


def comprobar_porcentajes_recu(ponderaciones_acta, porcentajes_efectivos, columnas):
    """
    Comprueba que los % de la 2ª convocatoria (columnas "EXAMEN RECU"
    y "TREBALL RECU") sean los MISMOS que los de evaluación continua
    (FINAL y TO), tal y como exige la normativa del departamento.
    """

    errores = []

    columna_examen_recu = columnas.get("examen_recu")
    columna_to_recu = columnas.get("to_recu")

    if columna_examen_recu:
        valor_acta = _porcentaje(ponderaciones_acta.get(columna_examen_recu))
        esperado = porcentajes_efectivos.get("FINAL", 0)
        if valor_acta != esperado:
            errores.append({
                "campo": "EXAMEN RECU (2ª convo)",
                "maestro": esperado,
                "acta": valor_acta,
            })

    if columna_to_recu:
        valor_acta = _porcentaje(ponderaciones_acta.get(columna_to_recu))
        esperado = porcentajes_efectivos.get("TO", 0)
        if valor_acta != esperado:
            errores.append({
                "campo": "TREBALL RECU (2ª convo)",
                "maestro": esperado,
                "acta": valor_acta,
            })

    return errores


def _nombre_alumno(alumno):

    nombre = str(alumno.get("NOMBRE", "")).strip()
    apellidos = str(alumno.get("APELLIDOS", "")).strip()

    if apellidos.lower() == "nan":
        apellidos = ""
    if nombre.lower() == "nan":
        nombre = ""

    return f"{apellidos} {nombre}".strip()


def auditar_notas(df_alumnos, porcentajes_efectivos, columnas):
    """
    Recorre a los alumnos y compara la nota calculada por SIVAA con
    la nota puesta por el profesor, aplicando todas las reglas
    (NP, asistencia, forzado a 4, redondeo).

    Devuelve un diccionario con listas separadas por tipo de
    incidencia, para poder presentarlas de forma clara en el informe:

        errores_nota          -> la nota no coincide con el cálculo
        errores_np             -> debería ser NP y no lo es (o al revés)
        errores_redondeo       -> nota bien pero sin redondear a 1 decimal
        no_evaluables          -> no se ha podido comprobar con garantías
        avisos_asistencia      -> alumnos con +15% de faltas (informativo)
        forzados_a_4            -> alumnos a los que se les ha forzado la nota a 4 (informativo)
    """

    resultado = {
        "errores_nota": [],
        "errores_np": [],
        "errores_redondeo": [],
        "no_evaluables": [],
        "avisos_asistencia": [],
        "forzados_a_4": [],
    }

    for _, alumno in df_alumnos.iterrows():

        nombre_completo = _nombre_alumno(alumno)

        if not nombre_completo:
            continue

        comparacion = comparar_nota(alumno, porcentajes_efectivos, columnas)

        tipo = comparacion["tipo"]
        detalle = comparacion["detalle"]

        if detalle.get("exceso_faltas"):
            resultado["avisos_asistencia"].append({
                "Alumno": nombre_completo,
                "Faltas %": alumno.get(columnas["faltas"]),
            })

        if detalle.get("forzado_a_4"):
            resultado["forzados_a_4"].append({
                "Alumno": nombre_completo,
                "Motivo": detalle.get("motivo_forzado"),
            })

        if tipo == "correcto":
            continue

        if tipo == "no_evaluable":
            resultado["no_evaluables"].append({
                "Alumno": nombre_completo,
                "Valor original": comparacion.get("nota_profesor_original"),
                "Nota SIVAA": comparacion.get("nota_sivaa"),
            })

        elif tipo in ("np_incumplida", "np_injustificada"):
            resultado["errores_np"].append({
                "Alumno": nombre_completo,
                "Tipo": tipo,
                "Nota SIVAA": comparacion.get("nota_sivaa"),
                "Valor profesor": comparacion.get("nota_profesor_original", comparacion.get("nota_profesor")),
            })

        elif tipo == "redondeo":
            resultado["errores_redondeo"].append({
                "Alumno": nombre_completo,
                "Nota profesor": comparacion.get("nota_profesor"),
                "Nota SIVAA": comparacion.get("nota_sivaa"),
            })

        elif tipo == "nota_incorrecta":
            resultado["errores_nota"].append({
                "Alumno": nombre_completo,
                "Nota profesor": comparacion.get("nota_profesor"),
                "Nota SIVAA": comparacion.get("nota_sivaa"),
            })

    return resultado


def _acta_tiene_datos_de_segunda_convocatoria(df_alumnos, columnas):
    """
    Comprueba si el acta tiene ALGÚN dato relleno en las columnas de
    2ª convocatoria (examen recu, TO recu o nota final 2 convo), para
    cualquier alumno. Si no hay nada relleno en ninguna, se entiende
    que el excel es solo de 1ª convocatoria (la 2ª aún no se ha
    celebrado) y no tiene sentido auditarla ni marcar nada como falta.
    """

    columnas_a_mirar = [
        columnas.get("examen_recu"),
        columnas.get("to_recu"),
        columnas.get("nota_final_2"),
    ]

    for columna in columnas_a_mirar:
        if not columna:
            continue
        for valor in df_alumnos.get(columna, []):
            if not esta_vacio(valor):
                return True

    return False


def auditar_segunda_convocatoria(df_alumnos, porcentajes_efectivos, columnas):
    """
    Igual que `auditar_notas`, pero para la 2ª convocatoria: solo
    entran en juego los alumnos que tenían el examen final y/o el TO
    suspendidos (o NP) en 1ª convocatoria.

    Devuelve las mismas categorías que auditar_notas, más:

        faltan_recu -> alumnos que debían recuperar examen y/o TO y
            no tienen nada puesto en esas columnas (ni nota ni NP)
        acta_solo_1a_convocatoria -> True si el excel no tiene NINGÚN
            dato de 2ª convocatoria (no ha llegado a celebrarse
            todavía), en cuyo caso no se marca nada como falta.
    """

    resultado = {
        "errores_nota": [],
        "errores_np": [],
        "errores_redondeo": [],
        "no_evaluables": [],
        "avisos_asistencia": [],
        "forzados_a_4": [],
        "faltan_recu": [],
        "acta_solo_1a_convocatoria": False,
    }

    if not columnas.get("examen_recu") and not columnas.get("to_recu"):
        # El acta no tiene columnas de 2ª convocatoria: no se audita.
        return resultado

    if not _acta_tiene_datos_de_segunda_convocatoria(df_alumnos, columnas):
        resultado["acta_solo_1a_convocatoria"] = True
        return resultado

    for _, alumno in df_alumnos.iterrows():

        nombre_completo = _nombre_alumno(alumno)

        if not nombre_completo:
            continue

        comparacion = comparar_nota_segunda_convocatoria(
            alumno, porcentajes_efectivos, columnas
        )

        tipo = comparacion["tipo"]
        detalle = comparacion["detalle"]

        if tipo == "no_aplica":
            continue

        if tipo == "falta_recu":
            que_falta = []
            if detalle["necesita_examen"] and detalle["falta_examen_recu"]:
                que_falta.append("examen final")
            if detalle["necesita_to"] and detalle["falta_to_recu"]:
                que_falta.append("TO")

            resultado["faltan_recu"].append({
                "Alumno": nombre_completo,
                "Falta": " y ".join(que_falta),
            })
            continue

        if detalle.get("exceso_faltas"):
            resultado["avisos_asistencia"].append({
                "Alumno": nombre_completo,
                "Faltas %": alumno.get(columnas["faltas"]),
            })

        if detalle.get("forzado_a_4"):
            resultado["forzados_a_4"].append({
                "Alumno": nombre_completo,
                "Motivo": detalle.get("motivo_forzado"),
            })

        if tipo == "correcto":
            continue

        if tipo == "no_evaluable":
            resultado["no_evaluables"].append({
                "Alumno": nombre_completo,
                "Valor original": comparacion.get("nota_profesor_original"),
                "Nota SIVAA": comparacion.get("nota_sivaa"),
            })

        elif tipo in ("np_incumplida", "np_injustificada"):
            resultado["errores_np"].append({
                "Alumno": nombre_completo,
                "Tipo": tipo,
                "Nota SIVAA": comparacion.get("nota_sivaa"),
                "Valor profesor": comparacion.get("nota_profesor_original", comparacion.get("nota_profesor")),
            })

        elif tipo == "redondeo":
            resultado["errores_redondeo"].append({
                "Alumno": nombre_completo,
                "Nota profesor": comparacion.get("nota_profesor"),
                "Nota SIVAA": comparacion.get("nota_sivaa"),
            })

        elif tipo == "nota_incorrecta":
            resultado["errores_nota"].append({
                "Alumno": nombre_completo,
                "Nota profesor": comparacion.get("nota_profesor"),
                "Nota SIVAA": comparacion.get("nota_sivaa"),
            })

    return resultado
