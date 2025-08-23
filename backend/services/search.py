# backend/services/buscar.py
from db import matriz, inicializar

# -----------------------------
# Helpers sobre la grilla
# -----------------------------
def posiciones(nombre):
    """Todas las posiciones (fila, col, idx) donde aparece la persona."""
    out = []
    for i, fila in enumerate(matriz):
        for j, celda in enumerate(fila):
            if nombre in celda:
                out.append((i, j, celda.index(nombre)))
    return out

def cols_en_fila(nombre, fila):
    """Conjunto de columnas donde aparece 'nombre' en la fila dada."""
    cols = set()
    if 0 <= fila < len(matriz):
        for j, celda in enumerate(matriz[fila]):
            if nombre in celda:
                cols.add(j)
    return cols

def columnas_pareja_de(nombre):
    """Columnas donde 'nombre' aparece como parte de pareja (fila 2)."""
    return cols_en_fila(nombre, 2)

def hermanos_de(nombre):
    """Hermanos consanguíneos (fila 1 y fila 3)."""
    hermanos = set()
    for fila in (1, 3):
        for j, celda in enumerate(matriz[fila]):
            if nombre in celda:
                hermanos.update(x for x in celda if x != nombre)
    return hermanos

def esposos_de(nombre):
    """Pareja(s) (fila 0 y fila 2)."""
    esposos = set()
    for fila in (0, 2):
        for j, celda in enumerate(matriz[fila]):
            if nombre in celda:
                esposos.update(x for x in celda if x != nombre)
    return esposos

def padres_de_hijo(hijo):
    """Padres (pareja de fila 2) del hijo (fila 3) según su columna."""
    padres = set()
    for j, celda in enumerate(matriz[3]):
        if hijo in celda:
            padres.update(matriz[2][j])  # pareja de esa columna
    return tuple(padres)  # (p1, p2) o vacío

def padres_de_persona(nombre):
    """Padres de alguien que está en fila 1 (sus papás en fila 0) o
    si es un hijo en fila 3 (sus papás en fila 2). Devuelve set."""
    out = set()
    # Si está en fila 1 -> padres en fila 0, misma columna
    for j, celda in enumerate(matriz[1]):
        if nombre in celda:
            out.update(matriz[0][j])
    # Si está en fila 3 -> padres en fila 2, misma columna
    for j, celda in enumerate(matriz[3]):
        if nombre in celda:
            out.update(matriz[2][j])
    return out

def abuelos_de(h):
    """Abuelos: los de fila 0 de la misma columna del nieto (fila 3)."""
    ab = set()
    for j, celda in enumerate(matriz[3]):
        if h in celda:
            ab.update(matriz[0][j])
    return ab

# -----------------------------
# Reglas de relación
# -----------------------------
def relacion(a, b):
    pos_a = posiciones(a)
    pos_b = posiciones(b)
    if not pos_a or not pos_b:
        return f"No se encontró a {a} o {b}"

    # 1) MISMA CELDA → pareja (filas pares) / hermanos (filas impares)
    for (fa, ca, ia) in pos_a:
        for (fb, cb, ib) in pos_b:
            if fa == fb and ca == cb and ia != ib:
                if fa % 2 == 0:
                    return f"{a} y {b} son pareja"
                else:
                    return f"{a} y {b} son hermanos"

    # 2) PADRE / HIJO (mismo árbol/columna, niveles válidos)
    for (fa, ca, _) in pos_a:
        for (fb, cb, _) in pos_b:
            if ca == cb:
                if (fa, fb) in ((0, 1), (2, 3)):
                    return f"{a} es padre/madre de {b}"
                if (fb, fa) in ((0, 1), (2, 3)):
                    return f"{a} es hijo/a de {b}"

    # 3) ABUELO / NIETO (solo 0 -> 3 en la MISMA columna)
    for (fa, ca, _) in pos_a:
        for (fb, cb, _) in pos_b:
            if ca == cb and fa == 0 and fb == 3:
                return f"{a} es abuelo/a de {b}"
            if ca == cb and fb == 0 and fa == 3:
                return f"{a} es nieto/a de {b}"

    # 4) SUEGRO / YERNO-NUERA
    row0_len = len(matriz[0]) if len(matriz) > 0 else 0
    for j in columnas_pareja_de(b):
        if 0 <= j < row0_len and a in matriz[0][j]:
            return f"{a} es suegro/a de {b}"
    for j in columnas_pareja_de(a):
        if 0 <= j < row0_len and b in matriz[0][j]:
            return f"{a} es yerno/nuera de {b}"

    esposos_a = esposos_de(a)
    esposos_b = esposos_de(b)
    for e in esposos_b:
        if padres_de_persona(e) & {a}:
            return f"{a} es suegro/a de {b}"
    for e in esposos_a:
        if padres_de_persona(e) & {b}:
            return f"{a} es yerno/nuera de {b}"

    # 5) TÍO / SOBRINO (incluye político)
    padres_b = padres_de_hijo(b)
    if padres_b:
        p1, p2 = list(padres_b)[0], list(padres_b)[1]
        if a in hermanos_de(p1) or a in hermanos_de(p2):
            return f"{a} es tío/tía de {b}"
        for h in (hermanos_de(p1) | hermanos_de(p2)):
            if a in esposos_de(h):
                return f"{a} es tío/tía de {b}"

    padres_a = padres_de_hijo(a)
    if padres_a:
        p1, p2 = list(padres_a)[0], list(padres_a)[1]
        if b in hermanos_de(p1) or b in hermanos_de(p2):
            return f"{a} es sobrino/a de {b}"
        for h in (hermanos_de(p1) | hermanos_de(p2)):
            if b in esposos_de(h):
                return f"{a} es sobrino/a de {b}"

     # 6) CUÑADOS (directos + indirectos)
    # --- directos
    for h in hermanos_de(a):
        if b in esposos_de(h):
            return f"{a} y {b} son cuñados"
    for e in esposos_de(a):
        if b in hermanos_de(e):
            return f"{a} y {b} son cuñados"
    for h in hermanos_de(b):
        if a in esposos_de(h):
            return f"{a} y {b} son cuñados"
    for e in esposos_de(b):
        if a in hermanos_de(e):
            return f"{a} y {b} son cuñados"

    # --- indirectos: hermano de mi cuñado
    for h in hermanos_de(a):
        for cu in esposos_de(h):
            if b in hermanos_de(cu) or b in esposos_de(cu):
                return f"{a} y {b} son cuñados"
    for h in hermanos_de(b):
        for cu in esposos_de(h):
            if a in hermanos_de(cu) or a in esposos_de(cu):
                return f"{a} y {b} son cuñados"

    # --- indirectos: cuñado de mi hermano
    for h in hermanos_de(a):
        for cu in hermanos_de(b):
            if cu in esposos_de(h) or h in esposos_de(cu):
                return f"{a} y {b} son cuñados"
    for h in hermanos_de(b):
        for cu in hermanos_de(a):
            if cu in esposos_de(h) or h in esposos_de(cu):
                return f"{a} y {b} son cuñados"

    # --- cuñado de mi cuñado (segundo nivel)
    for cu1 in esposos_de(a) | hermanos_de(a):
        for cu2 in esposos_de(cu1) | hermanos_de(cu1):
            if b == cu2:
                return f"{a} y {b} son cuñados"
    for cu1 in esposos_de(b) | hermanos_de(b):
        for cu2 in esposos_de(cu1) | hermanos_de(cu1):
            if a == cu2:
                return f"{a} y {b} son cuñados"

    # 7) PRIMOS (hijos de hermanos)
    if cols_en_fila(a, 3) and cols_en_fila(b, 3):
        pa = padres_de_hijo(a)
        pb = padres_de_hijo(b)
        if pa and pb:
            pa1, pa2 = list(pa)
            pb1, pb2 = list(pb)
            if (pa1 in hermanos_de(pb1) or pa1 in hermanos_de(pb2) or
                pa2 in hermanos_de(pb1) or pa2 in hermanos_de(pb2)):
                return f"{a} y {b} son primos"

    return f"No se puede determinar relación directa entre {a} y {b}"


# -----------------------------
# Tests rápidos
# -----------------------------
if __name__ == "__main__":
    inicializar()
    print(relacion("A", "G"))
