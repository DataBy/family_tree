from db import matriz, inicializar

def encontrar_posiciones(nombre):
    posiciones = []
    for i, fila in enumerate(matriz):
        for j, celda in enumerate(fila):
            if nombre in celda:
                posiciones.append((i, j, celda.index(nombre)))
    return posiciones


def relacion(a, b):
    pos_a_list = encontrar_posiciones(a)
    pos_b_list = encontrar_posiciones(b)

    if not pos_a_list or not pos_b_list:
        return f"No se encontró a {a} o {b}"

    # 1. Misma celda → pareja/hermanos
    for (fila_a, col_a, idx_a) in pos_a_list:
        for (fila_b, col_b, idx_b) in pos_b_list:
            if fila_a == fila_b and col_a == col_b and idx_a != idx_b:
                if fila_a % 2 == 0:
                    return f"{a} y {b} son pareja"
                else:
                    return f"{a} y {b} son hermanos"

    # 2. Cuñados (fila par, distinta columna)
    for (fila_a, col_a, idx_a) in pos_a_list:
        for (fila_b, col_b, idx_b) in pos_b_list:
            if fila_a == fila_b and fila_a % 2 == 0 and col_a != col_b:
                return f"{a} y {b} son cuñados"

    # 3. Padre ↔ Hijo
    for (fila_a, col_a, idx_a) in pos_a_list:
        for (fila_b, col_b, idx_b) in pos_b_list:
            if col_a == col_b and fila_b == fila_a + 1:
                return f"{a} es padre/madre de {b}"
            if col_a == col_b and fila_a == fila_b + 1:
                return f"{a} es hijo/a de {b}"

    # 4. Abuelo ↔ Nieto (permitiendo columnas distintas)
    for (fila_a, col_a, idx_a) in pos_a_list:
        for (fila_b, col_b, idx_b) in pos_b_list:
            if abs(fila_a - fila_b) >= 2:
                return f"{a} es abuelo/a de {b}" if fila_a < fila_b else f"{a} es nieto/a de {b}"

    # 5. Tío ↔ Sobrino
    for (fila_a, col_a, idx_a) in pos_a_list:
        for (fila_b, col_b, idx_b) in pos_b_list:
            if abs(fila_a - fila_b) == 1 and col_a != col_b:
                return f"{a} es tío/tía de {b}" if fila_a < fila_b else f"{a} es sobrino/a de {b}"

    # 6. Primos (fila impar, distinta columna)
    for (fila_a, col_a, idx_a) in pos_a_list:
        for (fila_b, col_b, idx_b) in pos_b_list:
            if fila_a == fila_b and fila_a % 2 == 1 and col_a != col_b:
                return f"{a} y {b} son primos"

    return f"No se puede determinar relación directa entre {a} y {b}"


if __name__ == "__main__":
    inicializar()
    print("---- PAREJAS ----")
    print("A-B:", relacion("A", "B"))
    print("C-D:", relacion("C", "D"))
    print("E-H:", relacion("E", "H"))
    print("F-K:", relacion("F", "K"))
    print("G-L:", relacion("G", "L"))
    print("I-M:", relacion("I", "M"))

    print("\n---- HERMANOS ----")
    print("E-F:", relacion("E", "F"))
    print("E-G:", relacion("E", "G"))
    print("F-G:", relacion("F", "G"))
    print("H-I:", relacion("H", "I"))
    print("H-J:", relacion("H", "J"))
    print("I-J:", relacion("I", "J"))
    print("N-P:", relacion("N", "P"))
    print("N-Q:", relacion("N", "Q"))
    print("P-Q:", relacion("P", "Q"))
    print("R-S:", relacion("R", "S"))

    print("\n---- PADRES ↔ HIJOS ----")
    print("A-E:", relacion("A", "E"))
    print("B-F:", relacion("B", "F"))
    print("C-H:", relacion("C", "H"))
    print("D-I:", relacion("D", "I"))
    print("E-N:", relacion("E", "N"))
    print("F-O:", relacion("F", "O")) # Check
    print("H-R:", relacion("H", "R")) # Check
    print("I-T:", relacion("I", "T"))

    print("\n---- ABUELOS ↔ NIETOS ----")
    print("A-H:", relacion("A", "H")) # Check
    print("A-N:", relacion("A", "N"))
    print("C-K:", relacion("C", "K")) # Check
    print("C-S:", relacion("C", "S"))

    print("\n---- TÍOS ↔ SOBRINOS ----")
    print("E-R:", relacion("E", "R")) # Check
    print("F-S:", relacion("F", "S")) 
    print("H-N:", relacion("H", "N")) 
    print("I-O:", relacion("I", "O")) # Check

    print("\n---- PRIMOS ----")
    print("E-H:", relacion("E", "H"))   # OJO: debe seguir saliendo pareja
    print("E-I:", relacion("E", "I"))   # Check
    print("N-R:", relacion("N", "R")) 
    print("P-S:", relacion("P", "S"))

    print("\n---- CUÑADOS ----")
    print("E-K:", relacion("E", "K"))
    print("F-M:", relacion("F", "M"))
    print("G-I:", relacion("G", "I"))