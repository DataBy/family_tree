# services/buscador.py
from . import db
import unicodedata

# La app asigna aquí la matriz de la familia activa en cada /chat:
#   setattr(buscador, "matriz", matriz)
matriz: list[list[list[dict]]] = []

# -----------------------------
# Normalización y utilidades
# -----------------------------
def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

def _full(p: dict) -> str:
    """Nombre completo canonizado desde el dict persona."""
    nc = p.get("nombre_completo")
    return nc if nc else f"{p.get('nombre','')} {p.get('apellidos','')}"

def _in_celda(celda: list[dict], nombre: str) -> int:
    """Índice si hay match por nombre completo normalizado; -1 si no está."""
    target = _norm(nombre)
    for i, person in enumerate(celda):
        if _norm(_full(person)) == target:
            return i
    return -1

def _has(names: set[str], name: str) -> bool:
    """Miembro por comparación normalizada."""
    t = _norm(name)
    return any(_norm(x) == t for x in names)

# -----------------------------
# Helpers sobre la grilla
# -----------------------------
def posiciones(nombre: str):
    """Todas las posiciones (fila, col, idx) donde aparece la persona."""
    out = []
    for i, fila in enumerate(matriz or []):
        for j, celda in enumerate(fila):
            k = _in_celda(celda, nombre)
            if k != -1:
                out.append((i, j, k))
    return out

def cols_en_fila(nombre: str, fila: int):
    """Conjunto de columnas donde aparece 'nombre' en la fila dada."""
    cols = set()
    if 0 <= fila < len(matriz):
        for j, celda in enumerate(matriz[fila]):
            if _in_celda(celda, nombre) != -1:
                cols.add(j)
    return cols

def columnas_pareja_de(nombre: str):
    """Columnas donde 'nombre' aparece como parte de pareja (fila 2)."""
    return cols_en_fila(nombre, 2)

def hermanos_de(nombre: str) -> set[str]:
    """Hermanos consanguíneos (fila 1 y fila 3)."""
    hermanos = set()
    for fila in (1, 3):
        if fila < len(matriz):
            for j, celda in enumerate(matriz[fila]):
                k = _in_celda(celda, nombre)
                if k != -1:
                    for idx, p in enumerate(celda):
                        if idx != k:
                            hermanos.add(_full(p))
    return hermanos

def esposos_de(nombre: str) -> set[str]:
    """Pareja(s) (fila 0 y fila 2)."""
    esposos = set()
    for fila in (0, 2):
        if fila < len(matriz):
            for j, celda in enumerate(matriz[fila]):
                k = _in_celda(celda, nombre)
                if k != -1:
                    for idx, p in enumerate(celda):
                        if idx != k:
                            esposos.add(_full(p))
    return esposos

def padres_de_hijo(hijo: str) -> tuple[str, ...]:
    """Padres (pareja de fila 2) del hijo (fila 3) según su columna."""
    padres = set()
    if len(matriz) > 3:
        for j, celda in enumerate(matriz[3]):
            if _in_celda(celda, hijo) != -1 and 2 < len(matriz):
                for p in matriz[2][j]:
                    padres.add(_full(p))
    return tuple(padres)

def padres_de_persona(nombre: str) -> set[str]:
    """
    Padres de alguien que está en fila 1 (sus papás en fila 0) o
    si es un hijo en fila 3 (sus papás en fila 2).
    """
    out = set()
    if len(matriz) > 1:
        for j, celda in enumerate(matriz[1]):
            if _in_celda(celda, nombre) != -1:
                for p in matriz[0][j]:
                    out.add(_full(p))
    if len(matriz) > 3:
        for j, celda in enumerate(matriz[3]):
            if _in_celda(celda, nombre) != -1:
                for p in matriz[2][j]:
                    out.add(_full(p))
    return out

def abuelos_de(h: str) -> set[str]:
    """Abuelos: los de fila 0 de la misma columna del nieto (fila 3)."""
    ab = set()
    if len(matriz) > 3:
        for j, celda in enumerate(matriz[3]):
            if _in_celda(celda, h) != -1 and len(matriz) > 0:
                for p in matriz[0][j]:
                    ab.add(_full(p))
    return ab

# -----------------------------
# Reglas de relación
# -----------------------------
def relacion(a: str, b: str) -> str:
    pos_a = posiciones(a)
    pos_b = posiciones(b)
    if not pos_a or not pos_b:
        return f"No se encontró a {a} o {b}"

    # 1) MISMA CELDA → pareja (filas pares) / hermanos (filas impares)
    for (fa, ca, ia) in pos_a:
        for (fb, cb, ib) in pos_b:
            if fa == fb and ca == cb and ia != ib:
                if fa % 2 == 0:
                    return f"{a.title()} y {b.title()} son pareja"
                else:
                    return f"{a.title()} y {b.title()} son hermanos"

    # 2) PADRE / HIJO (mismo árbol/columna, niveles válidos)
    for (fa, ca, _) in pos_a:
        for (fb, cb, _) in pos_b:
            if ca == cb:
                if (fa, fb) in ((0, 1), (2, 3)):
                    return f"{a.title()} es padre/madre de {b.title()}"
                if (fb, fa) in ((0, 1), (2, 3)):
                    return f"{a.title()} es hijo/a de {b.title()}"

    # 3) ABUELO / NIETO (solo 0 -> 3 en la MISMA columna)
    for (fa, ca, _) in pos_a:
        for (fb, cb, _) in pos_b:
            if ca == cb and fa == 0 and fb == 3:
                return f"{a.title()} es abuelo/a de {b.title()}"
            if ca == cb and fb == 0 and fa == 3:
                return f"{a.title()} es nieto/a de {b.title()}"

    # 4) SUEGRO / YERNO-NUERA
    row0_len = len(matriz[0]) if len(matriz) > 0 else 0
    for j in columnas_pareja_de(b):
        if 0 <= j < row0_len and _in_celda(matriz[0][j], a) != -1:
            return f"{a.title()} es suegro/a de {b.title()}"
    for j in columnas_pareja_de(a):
        if 0 <= j < row0_len and _in_celda(matriz[0][j], b) != -1:
            return f"{a.title()} es yerno/nuera de {b.title()}"

    esposos_a = esposos_de(a)
    esposos_b = esposos_de(b)
    for e in esposos_b:
        if _has(padres_de_persona(e), a):
            return f"{a.title()} es suegro/a de {b.title()}"
    for e in esposos_a:
        if _has(padres_de_persona(e), b):
            return f"{a.title()} es yerno/nuera de {b.title()}"

    # 5) TÍO / SOBRINO (incluye político)
    padres_b = padres_de_hijo(b)
    if padres_b:
        p1, p2 = list(padres_b)[0], list(padres_b)[1]
        if _has(hermanos_de(p1), a) or _has(hermanos_de(p2), a):
            return f"{a.title()} es tío/tía de {b.title()}"
        for h in (hermanos_de(p1) | hermanos_de(p2)):
            if _has(esposos_de(h), a):
                return f"{a.title()} es tío/tía de {b.title()}"

    padres_a = padres_de_hijo(a)
    if padres_a:
        p1, p2 = list(padres_a)[0], list(padres_a)[1]
        if _has(hermanos_de(p1), b) or _has(hermanos_de(p2), b):
            return f"{a.title()} es sobrino/a de {b.title()}"
        for h in (hermanos_de(p1) | hermanos_de(p2)):
            if _has(esposos_de(h), b):
                return f"{a.title()} es sobrino/a de {b.title()}"

    # 6) CUÑADOS (directos + indirectos)
    for h in hermanos_de(a):
        if _has(esposos_de(h), b): return f"{a.title()} y {b.title()} son cuñados"
    for e in esposos_de(a):
        if _has(hermanos_de(e), b): return f"{a.title()} y {b.title()} son cuñados"
    for h in hermanos_de(b):
        if _has(esposos_de(h), a): return f"{a.title()} y {b.title()} son cuñados"
    for e in esposos_de(b):
        if _has(hermanos_de(e), a): return f"{a.title()} y {b.title()} son cuñados"

    # indirectos: hermano de mi cuñado
    for h in hermanos_de(a):
        for cu in esposos_de(h):
            if _has(hermanos_de(cu), b) or _has(esposos_de(cu), b):
                return f"{a.title()} y {b.title()} son cuñados"
    for h in hermanos_de(b):
        for cu in esposos_de(h):
            if _has(hermanos_de(cu), a) or _has(esposos_de(cu), a):
                return f"{a.title()} y {b.title()} son cuñados"

    # indirectos: cuñado de mi hermano
    for h in hermanos_de(a):
        for cu in hermanos_de(b):
            if _has(esposos_de(h), cu) or _has(esposos_de(cu), h):
                return f"{a.title()} y {b.title()} son cuñados"
    for h in hermanos_de(b):
        for cu in hermanos_de(a):
            if _has(esposos_de(h), cu) or _has(esposos_de(cu), h):
                return f"{a.title()} y {b.title()} son cuñados"

    # cuñado de mi cuñado (segundo nivel)
    for cu1 in esposos_de(a) | hermanos_de(a):
        for cu2 in esposos_de(cu1) | hermanos_de(cu1):
            if _norm(b) == _norm(cu2):
                return f"{a.title()} y {b.title()} son cuñados"
    for cu1 in esposos_de(b) | hermanos_de(b):
        for cu2 in esposos_de(cu1) | hermanos_de(cu1):
            if _norm(a) == _norm(cu2):
                return f"{a.title()} y {b.title()} son cuñados"

    # 7) PRIMOS (hijos de hermanos)
    if cols_en_fila(a, 3) and cols_en_fila(b, 3):
        pa = padres_de_hijo(a)
        pb = padres_de_hijo(b)
        if pa and pb:
            pa1, pa2 = list(pa)
            pb1, pb2 = list(pb)
            if (_has(hermanos_de(pb1), pa1) or _has(hermanos_de(pb2), pa1) or
                _has(hermanos_de(pb1), pa2) or _has(hermanos_de(pb2), pa2)):
                return f"{a.title()} y {b.title()} son primos"

    return f"No se puede determinar relación directa entre {a} y {b}"
