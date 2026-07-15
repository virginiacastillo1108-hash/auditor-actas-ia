import argparse
import os
import sys

from acta import Acta
from maestro import cargar_maestro, buscar_asignatura, obtener_porcentajes
from auditor import (
    comprobar_porcentajes,
    comprobar_porcentajes_recu,
    auditar_notas,
    auditar_segunda_convocatoria,
    resolver_porcentajes_efectivos,
    _porcentaje,
)
from informe import generar_informe, guardar_informe
from config import EXCEL_MAESTRO


def auditar_acta(ruta_acta, ruta_maestro):
    """
    Ejecuta la auditoría completa de un acta y devuelve el
    texto del informe generado.
    """

    if isinstance(ruta_acta, str) and not os.path.exists(ruta_acta):
        raise FileNotFoundError(f"No se encuentra el archivo del acta: {ruta_acta}")

    if isinstance(ruta_maestro, str) and not os.path.exists(ruta_maestro):
        raise FileNotFoundError(f"No se encuentra el excel maestro: {ruta_maestro}")

    # 1. Leer el acta
    acta = Acta(ruta_acta)
    asignatura = acta.obtener_asignatura()
    curso = acta.obtener_curso()
    ponderaciones_acta = acta.obtener_ponderaciones()
    alumnos = acta.obtener_alumnos()
    columnas = acta.columnas

    print(f"Asignatura: {asignatura}")
    print(f"Curso: {curso}")
    print(f"Nº de alumnos detectados: {len(alumnos)}\n")

    for concepto, nombre_col in columnas.items():
        if nombre_col is None:
            print(f"⚠️  No se ha encontrado la columna para '{concepto}' en el acta.")

    # 2. Leer el excel maestro y localizar la asignatura
    df_maestro = cargar_maestro(ruta_maestro)
    fila_maestro, porcentajes_ambiguos = buscar_asignatura(df_maestro, asignatura)

    if fila_maestro is None:
        raise ValueError(
            f"La asignatura '{asignatura}' no se ha encontrado en el excel maestro."
        )

    if porcentajes_ambiguos:
        print(
            f"⚠️  '{asignatura}' aparece varias veces en el excel maestro con "
            "porcentajes distintos: revisa que se ha cogido el grupo/curso correcto.\n"
        )

    porcentajes_maestro = obtener_porcentajes(fila_maestro)

    # 3. Comprobar que las ponderaciones del acta coinciden con el maestro
    errores_porcentajes = comprobar_porcentajes(
        ponderaciones_acta, porcentajes_maestro
    )

    # 4. Resolver los porcentajes "efectivos" para el cálculo (por si
    #    el maestro solo da un valor combinado de PA+TO, por ejemplo)
    porcentajes_efectivos = resolver_porcentajes_efectivos(
        porcentajes_maestro, ponderaciones_acta
    )

    # 5. Auditar las notas de cada alumno (tabla principal, 1ª convocatoria)
    resultado_notas = auditar_notas(alumnos, porcentajes_efectivos, columnas)

    # 5b. Comprobar % y auditar la 2ª convocatoria (recuperación)
    errores_porcentajes_recu = comprobar_porcentajes_recu(
        ponderaciones_acta, porcentajes_efectivos, columnas
    )
    resultado_notas_recu = auditar_segunda_convocatoria(
        alumnos, porcentajes_efectivos, columnas
    )

    # 6. Auditar la sección DX, si existe
    tiene_dx = acta.tiene_seccion_dx()
    resultado_notas_dx = None

    if tiene_dx:
        alumnos_dx = acta.obtener_alumnos_dx()
        if alumnos_dx.empty:
            resultado_notas_dx = {
                "errores_nota": [], "errores_np": [], "errores_redondeo": [],
                "no_evaluables": [], "avisos_asistencia": [], "forzados_a_4": [],
            }
        else:
            ponderaciones_dx = acta.obtener_ponderaciones_dx()
            # Los porcentajes efectivos de la sección DX son los que
            # trae la propia acta en esa sección (normalmente solo
            # FINAL y TO), no los del excel maestro.
            porcentajes_dx = {
                "PARCIAL 1": _porcentaje(ponderaciones_dx.get(columnas["parcial1"])),
                "PARCIAL 2": _porcentaje(ponderaciones_dx.get(columnas["parcial2"])),
                "FINAL": _porcentaje(ponderaciones_dx.get(columnas["examen"])),
                "TO": _porcentaje(ponderaciones_dx.get(columnas["to"])),
                "PA": _porcentaje(ponderaciones_dx.get(columnas["pa"])),
            }
            resultado_notas_dx = auditar_notas(alumnos_dx, porcentajes_dx, columnas)

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
    )

    return informe, asignatura, curso, len(alumnos)


def main():

    parser = argparse.ArgumentParser(
        description="SIVAA - Auditor inteligente de actas de asignaturas"
    )
    parser.add_argument(
        "acta",
        nargs="?",
        default="data/1_BDM_IT_Applied_to_Marketing_Lilit_DElia.xlsx",
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
