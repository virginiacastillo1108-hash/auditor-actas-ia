from lector_excel import leer_excel
from auditor import comprobar_columnas
print("=================================")
print(" SIVAA - Auditor Inteligente")
print("=================================")

archivo = "data/1 BDM_IT Applied to Marketing_Lilit DElia.xlsx"

df = leer_excel(archivo)
errores = comprobar_columnas(df)

print("\nComprobación de columnas")
print("------------------------")

if len(errores) == 0:
    print("✅ Todas las columnas obligatorias existen.")
else:
    print("❌ Faltan las siguientes columnas:")
    for error in errores:
        print("-", error)
print("\nInformación del acta")
print("--------------------")
print(f"Número de alumnos: {len(df)-2}")
print(f"Número de columnas: {len(df.columns)}")

print("\nColumnas encontradas:")
print(df.columns.tolist())