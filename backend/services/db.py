# services/db.py
# Estructura: { "NombreFamilia": matriz }
# Donde matriz = lista de filas (niveles generacionales)
#   cada fila = lista de columnas (subfamilias)
#   cada celda = lista de personas (dicts)

from typing import Dict, List, Any

FamiliaMatriz = List[List[List[dict]]]
familias: Dict[str, FamiliaMatriz] = {}


def crear_familia(nombre: str) -> bool:
    """Crea una familia con matriz vacía. Devuelve False si ya existe o nombre vacío."""
    nombre = (nombre or "").strip()
    if not nombre or nombre in familias:
        return False
    familias[nombre] = []  # matriz vacía
    return True


def listar_familias() -> List[str]:
    """Lista los nombres de familias existentes."""
    return list(familias.keys())


def existe_familia(nombre: str) -> bool:
    return nombre in familias


def obtener_matriz(nombre: str) -> FamiliaMatriz | None:
    """Devuelve la matriz de una familia o None si no existe."""
    return familias.get(nombre)


def limpiar_familia(nombre: str) -> bool:
    """Resetea la matriz de una familia concreta."""
    if nombre in familias:
        familias[nombre] = []
        return True
    return False


def limpiar_todo() -> None:
    """Elimina todas las familias y datos (¡cuidado!)."""
    familias.clear()


def _tamano_dinamico(matriz: FamiliaMatriz, fila: int, columna: int) -> None:
    """Asegura que la matriz tenga al menos [fila][columna]."""
    while len(matriz) <= fila:
        matriz.append([])
    while len(matriz[fila]) <= columna:
        matriz[fila].append([])


def agregar_persona(persona: dict, nombre_familia: str, fila: int, columna: int) -> None:
    """
    Inserta una persona en la familia y posición dados.
    Lanza ValueError si la familia no existe.
    """
    if not existe_familia(nombre_familia):
        raise ValueError("Familia no seleccionada o no existe")

    m = familias[nombre_familia]
    _tamano_dinamico(m, fila, columna)
    m[fila][columna].append(persona)
