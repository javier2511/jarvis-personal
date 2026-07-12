estado = {
    "ultimo_modulo": None,
    "ultima_accion": None
}

def actualizar_estado(modulo, accion):
    estado["ultimo_modulo"] = modulo
    estado["ultima_accion"] = accion

def obtener_contexto():
    return estado