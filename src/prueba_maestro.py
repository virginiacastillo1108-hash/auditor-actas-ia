from maestro import cargar_maestro, buscar_asignatura, obtener_porcentajes

df = cargar_maestro("data/excel_maestro.xlsx")

fila = buscar_asignatura(
    df,
    "IT Applied to Marketing"
)

print()

print("FILA ENCONTRADA")

print(fila)

print()

print("PORCENTAJES")

print(obtener_porcentajes(fila))