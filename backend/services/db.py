# Acá generamos una matriz dinámica dónde será utilizada cómo base de datos de las personas.

matriz = []

def tamano_dinamico(fila, columna):
    # Regula la cantidad de filas
    while len(matriz) <= fila:
        matriz.append([])
    
    # Regula la cantidad de columnas
    while len(matriz[fila]) <= columna:
        matriz[fila].append([])

def agregar_personas(nombre, fila, columna):
    tamano_dinamico(fila, columna)
    matriz[fila][columna].append(nombre)

def inicializar():  # Fila, Columna
    # Fila 0
    agregar_personas("A", 0, 0)
    agregar_personas("B", 0, 0)   # pareja A-B
    agregar_personas("C", 0, 1)
    agregar_personas("D", 0, 1)   # pareja C-D

    # Fila 1
    agregar_personas("E", 1, 0)
    agregar_personas("F", 1, 0)
    agregar_personas("G", 1, 0)   # hermanos E-F-G
    agregar_personas("H", 1, 1)
    agregar_personas("I", 1, 1)
    agregar_personas("J", 1, 1)   # hermanos H-I-J

    # Fila 2
    agregar_personas("E", 2, 0)
    agregar_personas("H", 2, 0)   # pareja E-H
    agregar_personas("F", 2, 1)
    agregar_personas("K", 2, 1)   # pareja F-K
    agregar_personas("G", 2, 2)
    agregar_personas("L", 2, 2)   # pareja G-L
    agregar_personas("I", 2, 3)
    agregar_personas("M", 2, 3)   # pareja I-M

    # Fila 3
    agregar_personas("N", 3, 0)
    agregar_personas("P", 3, 0)
    agregar_personas("Q", 3, 0)   # hermanos N-P-Q
    agregar_personas("R", 3, 1)
    agregar_personas("S", 3, 1)   # hermanos R-S
    agregar_personas("O", 3, 2)   # hijo de G-L
    agregar_personas("T", 3, 3)   # hijo de I-M


if __name__ == "__main__":
    inicializar()
    print(matriz)