import math
import re


def es_numero(valor):
    """
    Comprueba si un valor es numérico Y no es NaN.

    OJO: float('nan') no lanza excepción en Python, así que
    antes esta función devolvía True para celdas vacías del
    Excel (que pandas representa como NaN), y ese NaN se colaba
    en todos los cálculos posteriores. Por eso se añade el
    chequeo explícito de math.isnan().
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
    Convierte un valor a float.
    Si está vacío o no es numérico, devuelve 0.0.
    """

    if not es_numero(valor):
        return 0.0

    return float(valor)


def extraer_nota(valor):
    """
    Extrae la parte numérica de una nota que puede venir
    acompañada de texto, por ejemplo:

        "MH 9,6"   -> 9.6
        "8,5"      -> 8.5
        8.5        -> 8.5
        "NP"       -> None (no evaluable)
        NaN        -> None (no evaluable)

    Devuelve None cuando no se puede interpretar como nota
    numérica, para que el llamador decida qué hacer (en vez
    de forzarlo silenciosamente a 0, que falseaba la comparación).
    """

    if valor is None:
        return None

    if es_numero(valor):
        return float(valor)

    texto = str(valor).strip().upper()

    if texto in ("", "NAN", "NONE", "NP", "NO PRESENTAT", "NO PRESENTADO"):
        return None

    # Normalizar coma decimal -> punto
    texto_normalizado = texto.replace(",", ".")

    # Buscar el primer número (con o sin decimales) dentro del texto
    coincidencia = re.search(r"-?\d+(\.\d+)?", texto_normalizado)

    if coincidencia:
        return float(coincidencia.group())

    return None


def calcular_nota(alumno, porcentajes):
    """
    Calcula la nota final según la regla real de la universidad:

    - Si el alumno TIENE examen final -> se usa el examen final
      (sustituye a los parciales): examen*FINAL% + trabajo*TO% + participacion*PA%
    - Si el alumno NO tiene examen final -> se usa evaluación
      continua con los parciales: parcial1*P1% + parcial2*P2% + trabajo*TO% + participacion*PA%

    Antes el código sumaba SIEMPRE ambas partes a la vez, lo que
    inflaba la nota muy por encima de 10 en cuanto había examen final.
    """

    parcial1 = numero(alumno.get("PARCIAL 1"))
    parcial2 = numero(alumno.get("PARCIAL 2"))
    trabajo = numero(alumno.get("TREBALL OBLIGAT"))
    participacion = numero(alumno.get("PARTICIPA ACTIVA"))

    valor_examen = alumno.get("EXAMEN FINAL/1 CONVO")
    tiene_examen = es_numero(valor_examen)

    p1 = porcentajes.get("PARCIAL 1", 0) / 100
    p2 = porcentajes.get("PARCIAL 2", 0) / 100
    p_final = porcentajes.get("FINAL", 0) / 100
    p_to = porcentajes.get("TO", 0) / 100
    p_pa = porcentajes.get("PA", 0) / 100

    if tiene_examen:
        examen = numero(valor_examen)
        nota = examen * p_final + trabajo * p_to + participacion * p_pa
    else:
        nota = parcial1 * p1 + parcial2 * p2 + trabajo * p_to + participacion * p_pa

    return round(nota, 2)


def comparar_nota(alumno, porcentajes):
    """
    Compara la nota calculada por SIVAA con la nota introducida
    por el profesor. Si la nota del profesor no se puede
    interpretar (texto no numérico, vacío...) se marca como
    "no evaluable" en vez de compararla igualmente contra 0.
    """

    nota_sivaa = calcular_nota(alumno, porcentajes)

    valor_original = alumno.get("NOTA FINAL (SIN RECU)")
    nota_profesor = extraer_nota(valor_original)

    if nota_profesor is None:
        return {
            "evaluable": False,
            "nota_sivaa": nota_sivaa,
            "nota_profesor_original": valor_original,
        }

    correcto = math.isclose(nota_sivaa, nota_profesor, abs_tol=0.05)

    return {
        "evaluable": True,
        "correcto": correcto,
        "nota_sivaa": nota_sivaa,
        "nota_profesor": nota_profesor,
    }
