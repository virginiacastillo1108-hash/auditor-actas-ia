from acta import Acta

acta = Acta("data/1 BDM_IT Applied to Marketing_Lilit DElia.xlsx")

for columna in acta.obtener_alumnos().columns:
    print(columna)
    