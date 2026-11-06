import argparse
import os
import sys

from acta import Acta
from maestro import cargar_maestro, buscar_asignatura, obtener_porcentajes, descripcion_fila
from auditor import (
    CONCEPTOS,
    comprobar_porcentajes,
    comprobar_porcentajes_recu,
    auditar_notas,
    auditar_segunda_convocatoria,
    resolver_porcentajes_efectivos,
    conceptos_no_soportados,
    _resultado_vacio,
)
from informe import generar_informe, guardar_informe
from correo import generar_correo_profesor
from config import EXCEL_MAESTRO


# Columnas sin las que no se puede auditar bien (nombre que se enseña al usuario)
COLUMNAS_IMPORTANTES = {
    "examen": "examen final",
    "to": "trabajo obligatorio (TO)",
    "nota_final": "nota final",
    "faltas": "faltas",
}


def _ejecutar_auditoria(ruta_acta, ruta_maestro, nombre_archivo=None):
    """
    Ejecuta la auditoría completa de un acta y devuelve TODOS los
    resultados intermedios en un diccionario (para poder generar
    tanto el informe de texto como, si hace falta, el correo al
    profesor, sin repetir cálculos).

    `nombre_archivo` (opcional) ayuda a reconocer al profesor cuando la
    misma asignatura aparece varias veces en el excel maestro; si no se
    indica, se saca de la propia ruta o del archivo subido.
    """

    if isinstance(ruta_acta, str) and not os.path.exists(ruta_acta):
        raise FileNotFoundError(f"No se encuentra el archivo del acta: {ruta_acta}")

    if isinstance(ruta_maestro, str) and not os.path.exists(ruta_maestro):
        raise FileNotFoundError(f"No se encuentra el excel maestro: {ruta_maestro}")

    avisos = []

    # 1. Leer el acta
    acta = Acta(ruta_acta, nombre_archivo)
    asignatura = acta.obtener_asignatura()
    curso = acta.obtener_curso()
    pct_acta = acta.obtener_ponderaciones()
    alumnos = acta.obtener_alumnos()
    columnas = acta.columnas

    for concepto, descripcion in COLUMNAS_IMPORTANTES.items():
        if columnas.get(concepto) is None:
            avisos.append(
                f"No se ha encontrado la columna de {descripcion} en el acta: "
                "los resultados que dependen de ella pueden no ser fiables."
            )

    # 2. Leer el excel maestro y localizar la asignatura
    df_maestro = cargar_maestro(ruta_maestro)

    busqueda = buscar_asignatura(
        df_maestro,
        acta.candidatos_asignatura(),
        acta.candidatos_curso(),
        acta.nombre_archivo,
    )

    if busqueda["fila"] is None:
        sugerencias = busqueda.get("sugerencias") or []
        detalle = (
            " Los nombres más parecidos del maestro son: " + "; ".join(sugerencias) + "."
            if sugerencias else ""
        )
        raise ValueError(
            f"La asignatura '{asignatura}' no se ha encontrado en el excel maestro.{detalle}"
        )

    fila_maestro = busqueda["fila"]
    maestro_usado = descripcion_fila(fila_maestro)

    if busqueda.get("ambiguo"):
        avisos.append(
            "Esta asignatura aparece en el excel maestro con porcentajes distintos para "
            "otros grupos/cursos. Se ha usado la fila indicada arriba; si no es la "
            "correcta, revisa estas otras: " + " | ".join(busqueda["alternativas"])
        )

    porcentajes_maestro = obtener_porcentajes(fila_maestro)

    if not porcentajes_maestro:
        raise ValueError(
            f"No he podido leer los porcentajes de '{maestro_usado}' en el excel maestro."
        )

    # 3. Comprobar que las ponderaciones del acta coinciden con el maestro
    errores_porcentajes = comprobar_porcentajes(pct_acta, porcentajes_maestro)

    # 4. Porcentajes "efectivos" para el cálculo: los del maestro; si el
    #    maestro solo da un valor combinado (PA+TO), el reparto lo pone el
    #    acta. Se guardan también los % tal como están escritos en el acta,
    #    para distinguir "nota mal calculada" de "% mal puesto".
    efectivos = resolver_porcentajes_efectivos(porcentajes_maestro, pct_acta)
    del_acta = {concepto: pct_acta.get(concepto, 0) for concepto in CONCEPTOS}

    if acta.to_incluye_pa:
        for porcentajes in (efectivos, del_acta):
            porcentajes["TO"] = porcentajes["TO"] + porcentajes["PA"]
            porcentajes["PA"] = 0

    no_soportados = conceptos_no_soportados(porcentajes_maestro)
    calculo_omitido = bool(no_soportados)

    errores_porcentajes_recu = comprobar_porcentajes_recu(pct_acta, efectivos, columnas)

    if calculo_omitido:
        avisos.append(
            "El maestro usa conceptos que SIVAA todavía no sabe calcular ("
            + ", ".join(no_soportados)
            + "): se comprueban los porcentajes pero NO se auditan las notas de los alumnos."
        )
        resultado_notas = _resultado_vacio()
        resultado_notas_recu = None
        resultado_notas_dx = None
        tiene_dx = False

    else:
        # 5. Auditar las notas de cada alumno (tabla principal, 1ª convocatoria)
        alternativos = del_acta if del_acta != efectivos else None
        resultado_notas = auditar_notas(alumnos, efectivos, columnas, alternativos)

        # 5b. Auditar la 2ª convocatoria (recuperación)
        resultado_notas_recu = auditar_segunda_convocatoria(alumnos, efectivos, columnas)

        # 6. Auditar la sección DX, si existe
        tiene_dx = acta.tiene_seccion_dx()
        resultado_notas_dx = None

        if tiene_dx:
            alumnos_dx, pct_dx, columnas_dx = acta.obtener_dx()

            if alumnos_dx.empty:
                resultado_notas_dx = _resultado_vacio()
            else:
                # Los % de la sección DX son los que trae la propia acta en esa
                # sección (normalmente solo FINAL y TO), no los del maestro.
                porcentajes_dx = {c: pct_dx.get(c, 0) for c in CONCEPTOS}
                resultado_notas_dx = auditar_notas(alumnos_dx, porcentajes_dx, columnas_dx)

    # 7. Generar el informe final
    informe = generar_informe(
        asignatura=asignatura,
        curso=curso,
        total_alumnos=len(alumnos),
        errores_porcentajes=errores_porcentajes,
        resultado_notas=resultado_notas,
        resultado_notas_dx=resultado_notas_dx,
        tiene_dx=tiene_dx,
        errores_porcentajes_recu=errores_porcentajes_recu,
        resultado_notas_recu=resultado_notas_recu,
        maestro_usado=maestro_usado,
        avisos=avisos,
        calculo_omitido=calculo_omitido,
    )

    return {
        "informe": informe,
        "asignatura": asignatura,
        "curso": curso,
        "total_alumnos": len(alumnos),
        "errores_porcentajes": errores_porcentajes,
        "resultado_notas": resultado_notas,
        "tiene_dx": tiene_dx,
        "resultado_notas_dx": resultado_notas_dx,
        "errores_porcentajes_recu": errores_porcentajes_recu,
        "resultado_notas_recu": resultado_notas_recu,
        "maestro_usado": maestro_usado,
        "avisos": avisos,
    }


def auditar_acta(ruta_acta, ruta_maestro, nombre_archivo=None):
    """
    Ejecuta la auditoría completa de un acta y devuelve el
    texto del informe generado (se mantiene esta función tal cual
    para no romper el código que ya la usa, p.ej. interfaz.py).
    """

    datos = _ejecutar_auditoria(ruta_acta, ruta_maestro, nombre_archivo)

    return datos["informe"], datos["asignatura"], datos["curso"], datos["total_alumnos"]


def auditar_acta_completo(ruta_acta, ruta_maestro, nombre_profesor="", nombre_archivo=None):
    """
    Igual que `auditar_acta`, pero además devuelve, en un diccionario,
    todos los datos intermedios y el correo (asunto, cuerpo) listo
    para enviar al profesor si hay algo que corregir.

    Devuelve un diccionario con, entre otras, las claves:
        informe, asignatura, curso, total_alumnos
        correo_asunto, correo_cuerpo (None, None si no hay nada que corregir)
    """

    datos = _ejecutar_auditoria(ruta_acta, ruta_maestro, nombre_archivo)

    asunto, cuerpo = generar_correo_profesor(
        asignatura=datos["asignatura"],
        curso=datos["curso"],
        errores_porcentajes=datos["errores_porcentajes"],
        resultado_notas=datos["resultado_notas"],
        tiene_dx=datos["tiene_dx"],
        resultado_notas_dx=datos["resultado_notas_dx"],
        errores_porcentajes_recu=datos["errores_porcentajes_recu"],
        resultado_notas_recu=datos["resultado_notas_recu"],
        nombre_profesor=nombre_profesor,
    )

    datos["correo_asunto"] = asunto
    datos["correo_cuerpo"] = cuerpo

    return datos


def main():

    parser = argparse.ArgumentParser(
        description="SIVAA - Auditor inteligente de actas de asignaturas"
    )
    parser.add_argument(
        "acta",
        help="Ruta al Excel del acta a auditar",
    )
    parser.add_argument(
        "--maestro",
        default=EXCEL_MAESTRO,
        help="Ruta al Excel maestro (por defecto, el de config.py)",
    )
    parser.add_argument(
        "--salida",
        default=None,
        help="Ruta donde guardar el informe (por defecto: informes/<asignatura>.txt)",
    )
    args = parser.parse_args()

    print("=================================")
    print(" SIVAA - Auditor Inteligente")
    print("=================================\n")

    try:
        informe, asignatura, curso, total_alumnos = auditar_acta(args.acta, args.maestro)
    except (FileNotFoundError, ValueError) as error:
        print(f"❌ {error}")
        sys.exit(1)

    print(informe)

    ruta_salida = args.salida or os.path.join(
        "informes", f"{asignatura.replace('/', '-')}.txt"
    )
    guardar_informe(informe, ruta_salida)
    print(f"\n📄 Informe guardado en: {ruta_salida}")


if __name__ == "__main__":
    main()
