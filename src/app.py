import argparse
import os
import sys

from acta import Acta
from maestro import cargar_maestro, buscar_asignatura, obtener_porcentajes
from auditor import comprobar_porcentajes, auditar_notas
from informe import generar_informe, guardar_informe
from config import EXCEL_MAESTRO


def auditar_acta(ruta_acta, ruta_maestro):
    """
    Ejecuta la auditoría completa de un acta y devuelve el
    texto del informe generado.
    """

    # Cuando se llama desde la web, ruta_acta/ruta_maestro pueden ser
    # archivos subidos (objetos en memoria) en vez de rutas de texto.
    # La comprobación de "existe el archivo" solo tiene sentido si es
    # una ruta de texto (uso por terminal).
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

    print(f"Asignatura: {asignatura}")
    print(f"Curso: {curso}")
    print(f"Nº de alumnos detectados: {len(alumnos)}\n")

    # 2. Leer el excel maestro y localizar la asignatura
    df_maestro = cargar_maestro(ruta_maestro)
    fila_maestro = buscar_asignatura(df_maestro, asignatura)

    if fila_maestro is None:
        raise ValueError(
            f"La asignatura '{asignatura}' no se ha encontrado en el excel maestro."
        )

    porcentajes_maestro = obtener_porcentajes(fila_maestro)

    # 3. Comprobar que las ponderaciones del acta coinciden con el maestro
    errores_porcentajes = comprobar_porcentajes(
        ponderaciones_acta, porcentajes_maestro
    )

    # 4. Auditar las notas de cada alumno
    errores_notas, no_evaluables = auditar_notas(alumnos, porcentajes_maestro)

    # 5. Generar el informe final
    informe = generar_informe(
        asignatura=asignatura,
        curso=curso,
        total_alumnos=len(alumnos),
        errores_porcentajes=errores_porcentajes,
        errores_notas=errores_notas,
        no_evaluables=no_evaluables,
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
