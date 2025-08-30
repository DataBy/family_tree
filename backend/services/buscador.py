# services/buscador.py
from . import db
import unicodedata
from collections import deque

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

# =============================
# Helpers Preguntas antepasados, etc...
# =============================
def _children_of(nombre: str) -> set[str]:
    """
    Hijos directos de 'nombre' considerando ambas transiciones del modelo:
    fila0->fila1 (fundadores->hijos) y fila2->fila3 (parejas->hijos).
    """
    hijos = set()
    # fila 0 -> fila 1 (misma columna)
    if len(matriz) > 1:
        for j, celda in enumerate(matriz[0]):
            if _in_celda(celda, nombre) != -1 and j < len(matriz[1]):
                for h in matriz[1][j]:
                    hijos.add(_full(h))

    # fila 2 -> fila 3 (misma columna)
    if len(matriz) > 3:
        for j, celda in enumerate(matriz[2]):
            if _in_celda(celda, nombre) != -1 and j < len(matriz[3]):
                for h in matriz[3][j]:
                    hijos.add(_full(h))

    return hijos


def _esta_vivo(nombre: str) -> bool:
    """Devuelve True si existe alguna aparición de la persona sin fecha_defuncion."""
    target = _norm(nombre)
    for fila in (matriz or []):
        for celda in fila:
            for p in celda:
                if _norm(_full(p)) == target:
                    if not (p.get("fecha_defuncion") or "").strip():
                        return True
    return False


def primos_primer_grado(nombre: str) -> list[str]:
    """
    Primos de primer grado de 'nombre':
    hijos de los hermanos de cada uno de sus padres.
    """
    primos = set()
    padres = padres_de_hijo(nombre)
    if not padres:
        return []

    for padre in padres:
        for tio in hermanos_de(padre):
            primos.update(_children_of(tio))

    # quitarme a mí mismo (por duplicidad de nombres)
    primos = [n for n in primos if _norm(n) != _norm(nombre)]
    return sorted(primos)


def descendientes_vivos(nombre: str) -> list[str]:
    """
    Todos los descendientes vivos (hijos, nietos, bisnietos, ...) de 'nombre'.
    BFS por generaciones usando _children_of().
    """
    vivos = set()
    visitados = set()
    q = deque([nombre])

    while q:
        actual = q.popleft()
        key = _norm(actual)
        if key in visitados:
            continue
        visitados.add(key)

        for h in _children_of(actual):
            if _esta_vivo(h):
                vivos.add(h)
            q.append(h)

    vivos.discard(nombre)
    return sorted(vivos)





def _lookup_person(nombre: str) -> dict | None:
    """Devuelve el primer dict de persona cuyo nombre completo coincide (normalizado)."""
    t = _norm(nombre)
    for fila in (matriz or []):
        for celda in fila:
            k = _in_celda(celda, nombre)
            if k != -1:
                return celda[k]
    return None

def hijos_de_persona(nombre: str) -> set[str]:
    """
    Hijos de una persona (por columna):
      - Si está en fila 0 (parejas fundadoras) → hijos están en fila 1.
      - Si está en fila 2 (parejas de hijos)   → hijos están en fila 3.
    Devuelve nombres completos (set) en ambas capas si aplica.
    """
    hijos = set()
    if not matriz:
        return hijos

    # Caso fila 0 → hijos en fila 1
    if len(matriz) > 1 and len(matriz[0]) == len(matriz[1]):
        for j, celda in enumerate(matriz[0]):
            if _in_celda(celda, nombre) != -1:
                for p in matriz[1][j]:
                    hijos.add(_full(p))

    # Caso fila 2 → hijos en fila 3
    if len(matriz) > 3 and len(matriz[2]) == len(matriz[3]):
        for j, celda in enumerate(matriz[2]):
            if _in_celda(celda, nombre) != -1:
                for p in matriz[3][j]:
                    hijos.add(_full(p))

    return hijos


def parejas_con_mas_de_dos_hijos() -> list[str]:
    """
    Devuelve las parejas (nombre1 + nombre2) que tienen 2 o más hijos en común.
    """
    resultados = []
    if not matriz:
        return resultados

    for fila in (0, 2):  # filas de parejas
        if fila + 1 >= len(matriz):
            continue
        for j, celda in enumerate(matriz[fila]):
            if len(celda) >= 2:  # hay pareja
                hijos = matriz[fila + 1][j] if j < len(matriz[fila + 1]) else []
                if len(hijos) >= 2:
                    nombres_pareja = f"{_full(celda[0])} y {_full(celda[1])}"
                    resultados.append(nombres_pareja)
    return resultados



# =============================
# 2) Primos de primer grado
# =============================
def primos_primer_grado(nombre: str) -> list[str]:
    """
    Primos de 1er grado de X = hijos de los hermanos de sus padres.
    Funciona tanto si X está en fila 1 (sus primos también en fila 1)
    como si X está en fila 3 (sus primos también en fila 3).
    """
    padres = list(padres_de_persona(nombre))   # set[str] → list
    if not padres:
        return []

    t_nombre = _norm(nombre)
    t_vistos = set([t_nombre])
    primos = set()

    # Para cada padre/madre, tomar sus hermanos
    for p in padres:
        for tio_tia in hermanos_de(p):
            # Hijos del tío/tía = primos de X
            for h in hijos_de_persona(tio_tia):
                if _norm(h) not in t_vistos:
                    primos.add(h)
                    t_vistos.add(_norm(h))

    # Orden alfabético “bonito”
    return sorted(primos, key=lambda s: s.split()[-1] + " " + s.split()[0])


# =============================
# 3) Antepasados maternos
# =============================
def antepasados_maternos(nombre: str) -> list[str]:
    """
    Cadena materna: madre → abuela materna → bisabuela materna → ...
    Se basa en 'genero' del dict persona (busca 'fem' en minúsculas).
    """
    cadena = []
    cur = nombre
    t_vistos = set()

    while True:
        padres = list(padres_de_persona(cur))
        if not padres:
            break

        madre = None
        for p in padres:
            d = _lookup_person(p)
            if d and "fem" in (d.get("genero") or "").lower():
                madre = _full(d)
                break

        if not madre:
            break

        t = _norm(madre)
        if t in t_vistos:
            break  # por seguridad ante ciclos
        t_vistos.add(t)

        cadena.append(madre)
        cur = madre

    return cadena


# =============================
# 4) Descendientes vivos (recursivo/BFS)
# =============================
def descendientes_vivos(nombre: str) -> list[str]:
    """
    Todos los descendientes (hijos, nietos, etc.) que estén vivos actualmente
    (fecha_defuncion vacía). Recorre en anchura.
    """
    from collections import deque

    vivos = set()
    visit = set()
    q = deque()

    # arrancar con los hijos directos
    for h in hijos_de_persona(nombre):
        q.append(h)

    while q:
        person = q.popleft()
        t = _norm(person)
        if t in visit:
            continue
        visit.add(t)

        d = _lookup_person(person)
        # agregar si está vivo (fecha_defuncion vacía o falsy)
        if d and not (d.get("fecha_defuncion") or "").strip():
            vivos.add(_full(d))

        # en cualquier caso, seguir bajando a sus hijos
        for hh in hijos_de_persona(person):
            if _norm(hh) not in visit:
                q.append(hh)

    # Orden alfabético simple
    return sorted(vivos, key=lambda s: s.split()[-1] + " " + s.split()[0])







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
