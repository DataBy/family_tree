matriz = []

def tamano_dinamico(fila, columna):
    """Expande la matriz hasta la fila/columna necesarias."""
    while len(matriz) <= fila:
        matriz.append([])
    while len(matriz[fila]) <= columna:
        matriz[fila].append([])

def agregar_persona(persona, fila, columna):
    """
    Inserta una persona (diccionario) en la posición [fila][columna].
    - persona: dict con los datos de la persona
    - fila: nivel generacional
    - columna: sub-familia
    """
    tamano_dinamico(fila, columna)
    matriz[fila][columna].append(persona)

def limpiar():
    """Reinicia la base de datos (matriz vacía)."""
    global matriz
    matriz = []
