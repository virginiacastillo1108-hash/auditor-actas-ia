import math
import re
from decimal import Decimal, ROUND_HALF_UP


# =====================================================
# UTILIDADES BÁSICAS DE LECTURA DE CELDAS
# =====================================================

TEXTOS_VACIOS = ("", "NAN", "NONE")
TEXTOS_NP = ("NP", "NO PRESENTAT", "NO PRESENTADO")


def es_numero(valor):
    """
    Comprueba si un valor es numérico Y no es NaN.
    """

    if valor is None:
        return False

    try:
        numero_float = float(valor)
        return not math.isnan(numero_float)
    except (TypeError, ValueError):
        return False


def numero(valor):
    """
    Convierte un valor a float. Si está vacío o no es numérico,
    devuelve 0.0 (para poder sumarlo en las ponderaciones).
    """

    if not es_numero(valor):
        return 0.0

    return float(valor)


def es_no_presentado(valor):
    """
    Indica si una celda dice explícitamente "NP" (o variantes como
    "No presentat"/"No presentado").

    OJO: una celda VACÍA no es lo mismo que "NP". Vacía normalmente
    significa que el alumno ha liberado esa prueba (p.ej. el examen
    final cuando ha aprobado los parciales), mientras que "NP" es una
    marca explícita del profesor de que el alumno no se presentó.
    Esta distinción es clave para la regla de "NP siempre implica NP
    en la nota final".
    """

    if valor is None:
        return False

    if es_numero(valor):
        return False

    texto = str(valor).strip().upper()

    return texto in TEXTOS_NP


def esta_vacio(valor):
    """
    Celda vacía de verdad (ni número, ni texto, ni NP): NaN o "".
    """

    if valor is None:
        return True

    if es_numero(valor):
        return False

    texto = str(valor).strip().upper()

    return texto in TEXTOS_VACIOS


def extraer_nota(valor):
    """
    Extrae la parte numérica de una nota que puede venir acompañada
    de texto, por ejemplo:

        "MH 9,6"   -> 9.6
        "9,5MH"    -> 9.5
        "8,5"      -> 8.5
        8.5        -> 8.5
        "NP"       -> None (no evaluable / no presentado)
        NaN        -> None
        "EXP DISCIPL" -> None (texto no reconocido, revisar a mano)

    Devuelve None cuando no se puede interpretar como nota numérica,
    para que el llamador decida qué hacer.
    """

    if valor is None:
        return None

    if es_numero(valor):
        return float(valor)

    texto = str(valor).strip().upper()

    if texto in TEXTOS_VACIOS or texto in TEXTOS_NP:
        return None

    texto_normalizado = texto.replace(",", ".")

    coincidencia = re.search(r"-?\d+(\.\d+)?", texto_normalizado)

    if coincidencia:
        return float(coincidencia.group())

    return None


def redondeo_academico(valor, decimales=1):
    """
    Redondeo "de toda la vida" (mitad hacia arriba), que es el que se
    usa en el departamento para las notas finales:

        6.33 -> 6.3
        6.36 -> 6.4
        6.35 -> 6.4

    Python redondea "al par más cercano" (banker's rounding) por
    defecto, lo que en algunos casos daría 6.35 -> 6.3 o similar, así
    que usamos Decimal + ROUND_HALF_UP para que coincida con el
    criterio real del departamento.
    """

    if valor is None:
        return None

    cuantificador = Decimal("1").scaleb(-decimales)

    # Redondeamos primero a unos cuantos decimales "normales" para
    # eliminar el ruido de precisión de los floats (p.ej. que una
    # suma dé 8.149999999999999 en vez de 8.15 exacto), y así el
    # redondeo "mitad hacia arriba" no falle por ese ruido.
    valor_limpio = round(float(valor), 6)

    return float(
        Decimal(str(valor_limpio)).quantize(cuantificador, rounding=ROUND_HALF_UP)
    )


def tiene_mas_decimales_de_los_permitidos(valor_original, decimales=1):
    """
    Comprueba si una nota tal y como la ha puesto el profesor tiene
    más decimales de los que exige la normativa (1 decimal), por
    ejemplo un 6.043056 en vez de un 6.0.

    Se ignoran diferencias de menos de una milésima para no disparar
    falsos positivos por temas de representación de floats.
    """

    if valor_original is None:
        return False

    redondeado = redondeo_academico(valor_original, decimales)

    return abs(redondeado - valor_original) > 0.001


# =====================================================
# CÁLCULO DE LA NOTA FINAL
# =====================================================

UMBRAL_FALTAS = 15  # % de faltas a partir del cual aplica la regla de asistencia
UMBRAL_SUSPENSO = 5  # nota mínima para aprobar examen/TO
NOTA_FORZADA = 4.0


def calcular_nota_final(alumno, porcentajes, columnas):
    """
    Calcula la nota final de un alumno aplicando, en este orden, las
    reglas reales del departamento:

    1. Si el examen final o el TO están marcados como "NP" (no
       presentado), la nota final SIEMPRE es NP, sea lo que sea que
       haya en el resto de items.
    2. Si el alumno supera el 15% de faltas (asistencia < 85%), la
       nota final es SOLO la ponderación del examen final (los
       parciales no cuentan), y el alumno debe presentarse
       obligatoriamente al examen.
    3. En caso contrario, evaluación continua normal:
       - Si tiene examen final -> examen substituye a los parciales.
       - Si no tiene examen final -> se usan los parciales.
    4. Si el examen final o el TO están suspendidos (nota < 5) y la
       nota resultante del cálculo es superior a 4, se fuerza la
       nota final a un 4 (si ya daba 4 o menos, se deja tal cual).
    5. La nota final se redondea a 1 decimal (mitad hacia arriba).

    `columnas` es un diccionario con los nombres reales de columna a
    usar para cada concepto (para poder adaptarse a las variantes que
    aparecen en distintas actas), con claves:
        parcial1, parcial2, examen, to, pa, faltas

    Devuelve un diccionario con:
        nota: float o "NP"
        forzado_a_4: bool
        motivo_forzado: str o None
        exceso_faltas: bool
        no_evaluable: bool (True si no se ha podido calcular nada,
            p.ej. exceso de faltas pero examen vacío en vez de NP)
    """

    valor_parcial1 = alumno.get(columnas["parcial1"])
    valor_parcial2 = alumno.get(columnas["parcial2"])
    valor_examen = alumno.get(columnas["examen"])
    valor_to = alumno.get(columnas["to"])
    valor_pa = alumno.get(columnas["pa"])
    valor_faltas = alumno.get(columnas["faltas"]) if columnas.get("faltas") else None

    resultado = {
        "nota": None,
        "forzado_a_4": False,
        "motivo_forzado": None,
        "exceso_faltas": False,
        "no_evaluable": False,
    }

    # --- Regla 1: NP siempre gana ---
    if es_no_presentado(valor_examen) or es_no_presentado(valor_to):
        resultado["nota"] = "NP"
        return resultado

    p1 = porcentajes.get("PARCIAL 1", 0) / 100
    p2 = porcentajes.get("PARCIAL 2", 0) / 100
    p_final = porcentajes.get("FINAL", 0) / 100
    p_to = porcentajes.get("TO", 0) / 100
    p_pa = porcentajes.get("PA", 0) / 100

    parcial1 = numero(valor_parcial1)
    parcial2 = numero(valor_parcial2)
    to = numero(valor_to)
    pa = numero(valor_pa)

    tiene_examen = es_numero(valor_examen)
    faltas = numero(valor_faltas) if es_numero(valor_faltas) else None
    exceso_faltas = faltas is not None and faltas > UMBRAL_FALTAS
    resultado["exceso_faltas"] = exceso_faltas

    # --- Regla 2: exceso de faltas -> solo cuenta el examen ---
    if exceso_faltas:
        if not tiene_examen:
            # Debería haberse presentado obligatoriamente al examen;
            # si la celda está vacía (no "NP") no podemos calcular
            # nada con garantías: se marca para revisión manual.
            resultado["no_evaluable"] = True
            return resultado

        nota = numero(valor_examen) * p_final

    # --- Regla 3: evaluación continua normal ---
    elif tiene_examen:
        nota = numero(valor_examen) * p_final + to * p_to + pa * p_pa
    else:
        nota = parcial1 * p1 + parcial2 * p2 + to * p_to + pa * p_pa

    # --- Regla 4: forzado a 4 si examen o TO suspendidos ---
    examen_num = numero(valor_examen) if tiene_examen else None
    to_num = numero(valor_to) if es_numero(valor_to) else None

    suspenso_examen = examen_num is not None and examen_num < UMBRAL_SUSPENSO
    suspenso_to = to_num is not None and to_num < UMBRAL_SUSPENSO

    if (suspenso_examen or suspenso_to) and nota > NOTA_FORZADA:
        motivos = []
        if suspenso_examen:
            motivos.append("examen final suspendido")
        if suspenso_to:
            motivos.append("TO suspendido")

        nota = NOTA_FORZADA
        resultado["forzado_a_4"] = True
        resultado["motivo_forzado"] = " y ".join(motivos)

    # --- Regla 5: redondeo a 1 decimal ---
    resultado["nota"] = redondeo_academico(nota, 1)

    return resultado


def comparar_nota(alumno, porcentajes, columnas):
    """
    Compara la nota calculada por SIVAA con la nota puesta por el
    profesor, y clasifica el resultado en uno de estos tipos:

        "correcto"           -> todo cuadra
        "no_evaluable"        -> no se puede comparar con garantías
        "np_incumplida"       -> SIVAA dice que debería ser NP y no lo es
        "np_injustificada"    -> el profesor puso NP pero SIVAA calcula nota
        "redondeo"            -> la nota está bien pero no redondeada a 1 decimal
        "nota_incorrecta"     -> la nota no coincide con el cálculo de SIVAA
    """

    calculo = calcular_nota_final(alumno, porcentajes, columnas)

    valor_original = alumno.get(columnas["nota_final"])

    return _comparar(calculo, valor_original)


def _comparar(calculo, valor_original):
    """
    Lógica de comparación común entre 1ª y 2ª convocatoria: dado un
    cálculo (nota SIVAA + metadatos) y el valor que ha puesto el
    profesor, decide el tipo de incidencia.
    """

    if calculo["no_evaluable"]:
        return {
            "tipo": "no_evaluable",
            "nota_sivaa": None,
            "nota_profesor_original": valor_original,
            "detalle": calculo,
        }

    profesor_dice_np = es_no_presentado(valor_original)
    nota_profesor = extraer_nota(valor_original)
    if nota_profesor is not None:
        nota_profesor = round(nota_profesor, 6)

    # --- SIVAA dice que debería ser NP ---
    if calculo["nota"] == "NP":
        if profesor_dice_np:
            return {
                "tipo": "correcto",
                "nota_sivaa": "NP",
                "nota_profesor": "NP",
                "detalle": calculo,
            }
        return {
            "tipo": "np_incumplida",
            "nota_sivaa": "NP",
            "nota_profesor_original": valor_original,
            "detalle": calculo,
        }

    # --- SIVAA calcula una nota numérica ---
    if profesor_dice_np:
        return {
            "tipo": "np_injustificada",
            "nota_sivaa": calculo["nota"],
            "nota_profesor_original": valor_original,
            "detalle": calculo,
        }

    if nota_profesor is None:
        return {
            "tipo": "no_evaluable",
            "nota_sivaa": calculo["nota"],
            "nota_profesor_original": valor_original,
            "detalle": calculo,
        }

    if tiene_mas_decimales_de_los_permitidos(nota_profesor):
        return {
            "tipo": "redondeo",
            "nota_sivaa": calculo["nota"],
            "nota_profesor": nota_profesor,
            "detalle": calculo,
        }

    if math.isclose(calculo["nota"], nota_profesor, abs_tol=0.06):
        return {
            "tipo": "correcto",
            "nota_sivaa": calculo["nota"],
            "nota_profesor": nota_profesor,
            "detalle": calculo,
        }

    return {
        "tipo": "nota_incorrecta",
        "nota_sivaa": calculo["nota"],
        "nota_profesor": nota_profesor,
        "detalle": calculo,
    }


# =====================================================
# SEGUNDA CONVOCATORIA
# =====================================================
#
# Reglas (según indicación del departamento): se evalúa igual que la
# primera convocatoria (mismos % de FINAL/TO/PA que en evaluación
# continua). Solo se recupera lo que se suspendió en 1ª convocatoria:
# si el examen final estaba suspendido (o NP), el alumno debe volver
# a examinarse (columna "EXAMEN RECU"); si el TO estaba suspendido (o
# NP), debe volver a entregarlo (columna "TREBALL RECU"). Lo que ya
# estaba aprobado en 1ª convocatoria se mantiene tal cual.


def necesita_segunda_convocatoria(alumno, columnas):
    """
    Indica si un alumno necesita recuperar el examen y/o el TO,
    en función de sus notas de 1ª convocatoria.
    """

    valor_examen_1 = alumno.get(columnas["examen"])
    valor_to_1 = alumno.get(columnas["to"])

    necesita_examen = es_no_presentado(valor_examen_1) or (
        es_numero(valor_examen_1) and numero(valor_examen_1) < UMBRAL_SUSPENSO
    )
    necesita_to = es_no_presentado(valor_to_1) or (
        es_numero(valor_to_1) and numero(valor_to_1) < UMBRAL_SUSPENSO
    )

    return necesita_examen, necesita_to


def calcular_nota_segunda_convocatoria(alumno, porcentajes, columnas):
    """
    Calcula la nota de 2ª convocatoria de un alumno, usando los MISMOS
    % de FINAL/TO/PA que en evaluación continua.

    Devuelve un diccionario con:
        aplica: si el alumno tenía algo que recuperar
        necesita_examen / necesita_to: qué le tocaba recuperar
        nota: float o "NP" (o None si no aplica o no evaluable)
        forzado_a_4, motivo_forzado
        falta_examen_recu / falta_to_recu: si debía recuperar algo y
            la celda correspondiente está vacía (ni nota ni NP)
        no_evaluable
    """

    necesita_examen, necesita_to = necesita_segunda_convocatoria(alumno, columnas)

    resultado = {
        "aplica": necesita_examen or necesita_to,
        "necesita_examen": necesita_examen,
        "necesita_to": necesita_to,
        "nota": None,
        "forzado_a_4": False,
        "motivo_forzado": None,
        "exceso_faltas": False,
        "falta_examen_recu": False,
        "falta_to_recu": False,
        "no_evaluable": False,
    }

    if not resultado["aplica"]:
        return resultado

    valor_examen = (
        alumno.get(columnas["examen_recu"]) if necesita_examen
        else alumno.get(columnas["examen"])
    )
    valor_to = (
        alumno.get(columnas["to_recu"]) if necesita_to
        else alumno.get(columnas["to"])
    )
    valor_pa = alumno.get(columnas["pa"])
    valor_faltas = alumno.get(columnas["faltas"]) if columnas.get("faltas") else None

    if necesita_examen and esta_vacio(valor_examen):
        resultado["falta_examen_recu"] = True
    if necesita_to and esta_vacio(valor_to):
        resultado["falta_to_recu"] = True

    if resultado["falta_examen_recu"] or resultado["falta_to_recu"]:
        resultado["no_evaluable"] = True
        return resultado

    if es_no_presentado(valor_examen) or es_no_presentado(valor_to):
        resultado["nota"] = "NP"
        return resultado

    p_final = porcentajes.get("FINAL", 0) / 100
    p_to = porcentajes.get("TO", 0) / 100
    p_pa = porcentajes.get("PA", 0) / 100

    examen_num = numero(valor_examen)
    to_num = numero(valor_to)
    pa_num = numero(valor_pa)

    faltas = numero(valor_faltas) if es_numero(valor_faltas) else None
    exceso_faltas = faltas is not None and faltas > UMBRAL_FALTAS
    resultado["exceso_faltas"] = exceso_faltas

    if exceso_faltas:
        nota = examen_num * p_final
    else:
        nota = examen_num * p_final + to_num * p_to + pa_num * p_pa

    suspenso_examen = examen_num < UMBRAL_SUSPENSO
    suspenso_to = to_num < UMBRAL_SUSPENSO

    if (suspenso_examen or suspenso_to) and nota > NOTA_FORZADA:
        motivos = []
        if suspenso_examen:
            motivos.append("examen final (2ª convocatoria) suspendido")
        if suspenso_to:
            motivos.append("TO (2ª convocatoria) suspendido")

        nota = NOTA_FORZADA
        resultado["forzado_a_4"] = True
        resultado["motivo_forzado"] = " y ".join(motivos)

    resultado["nota"] = redondeo_academico(nota, 1)

    return resultado


def comparar_nota_segunda_convocatoria(alumno, porcentajes, columnas):
    """
    Igual que `comparar_nota`, pero para la 2ª convocatoria. Además
    de los tipos habituales, puede devolver:

        "no_aplica"        -> el alumno aprobó todo en 1ª convocatoria,
                               no tenía que hacer 2ª convocatoria
        "falta_recu"       -> tenía que recuperar examen y/o TO y la
                               celda correspondiente está vacía
    """

    calculo = calcular_nota_segunda_convocatoria(alumno, porcentajes, columnas)

    if not calculo["aplica"]:
        return {"tipo": "no_aplica", "detalle": calculo}

    if calculo["falta_examen_recu"] or calculo["falta_to_recu"]:
        return {"tipo": "falta_recu", "detalle": calculo}

    valor_original = alumno.get(columnas["nota_final_2"])

    return _comparar(calculo, valor_original)
