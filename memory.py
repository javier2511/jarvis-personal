import json

MEMORY_FILE = "memory.json"

def cargar_memoria():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        return {}

def guardar_memoria(memoria):
    with open(MEMORY_FILE, "w", encoding="utf-8") as archivo:
        json.dump(memoria, archivo, indent=4, ensure_ascii=False)

def guardar_dato(campo, valor):
    memoria = cargar_memoria()

    valor_actual = memoria.get(campo)

    if valor_actual == valor:
        return f"El dato '{campo}' ya estaba guardado como '{valor}'."

    memoria[campo] = valor

    historial_campo = f"historial_{campo}"

    if historial_campo not in memoria:
        memoria[historial_campo] = []

    if valor not in memoria[historial_campo]:
        memoria[historial_campo].append(valor)

    guardar_memoria(memoria)

    return f"He guardado {campo} = {valor}."

def consultar_dato(campo):
    memoria = cargar_memoria()

    if campo in memoria:
        return f"{campo}: {memoria[campo]}"

    return f"No tengo guardado el dato '{campo}'."