# tests/test_search.py
# Puedes correrlo con:
#   1) pytest -q
#   2) python tests/test_search.py   (auto-invoca pytest)

import importlib.util
from pathlib import Path
import sys
import pytest

# ---------- Carga robusta del módulo (search.py o buscar.py) ----------
def _load_search_module():
    here = Path(__file__).resolve()
    # Busca hacia arriba un directorio que contenga backend/services
    for base in [here.parent, *here.parents]:
        svc = base / "backend" / "services"
        if svc.is_dir():
            # AÑADIMOS services al sys.path para que 'from db import ...' funcione
            if str(svc) not in sys.path:
                sys.path.insert(0, str(svc))
            for fname in ("search.py", "buscar.py"):
                f = svc / fname
                if f.exists():
                    spec = importlib.util.spec_from_file_location("family_tree_search", f)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)  # type: ignore
                    return mod
    raise FileNotFoundError("No encontré backend/services/(search|buscar).py")

S = _load_search_module()

# ---------- Inicialización única ----------
@pytest.fixture(scope="session", autouse=True)
def _init_db():
    S.inicializar()

# ---------- Helpers de expectativa ----------
def exp_pareja(a, b):   return f"{a} y {b} son pareja"
def exp_hermanos(a, b): return f"{a} y {b} son hermanos"
def exp_padre(a, b):    return f"{a} es padre/madre de {b}"
def exp_hijo(a, b):     return f"{a} es hijo/a de {b}"
def exp_abuelo(a, b):   return f"{a} es abuelo/a de {b}"
def exp_nieto(a, b):    return f"{a} es nieto/a de {b}"
def exp_tio(a, b):      return f"{a} es tío/tía de {b}"
def exp_sobrino(a, b):  return f"{a} es sobrino/a de {b}"
def exp_cunados(a, b):  return f"{a} y {b} son cuñados"
def exp_primos(a, b):   return f"{a} y {b} son primos"
def exp_suegro(a, b):   return f"{a} es suegro/a de {b}"
def exp_yerno(a, b):    return f"{a} es yerno/nuera de {b}"

# ---------- PAREJAS ----------
@pytest.mark.parametrize("a,b,expected", [
    ("A","B",exp_pareja("A","B")), ("B","A",exp_pareja("B","A")),
    ("C","D",exp_pareja("C","D")), ("D","C",exp_pareja("D","C")),
    ("E","H",exp_pareja("E","H")), ("H","E",exp_pareja("H","E")),
    ("F","K",exp_pareja("F","K")), ("K","F",exp_pareja("K","F")),
    ("G","L",exp_pareja("G","L")), ("L","G",exp_pareja("L","G")),
    ("I","M",exp_pareja("I","M")), ("M","I",exp_pareja("M","I")),
])
def test_parejas(a,b,expected):
    assert S.relacion(a,b) == expected

# ---------- HERMANOS ----------
@pytest.mark.parametrize("a,b,expected", [
    ("E","F",exp_hermanos("E","F")), ("F","E",exp_hermanos("F","E")),
    ("E","G",exp_hermanos("E","G")), ("G","E",exp_hermanos("G","E")),
    ("F","G",exp_hermanos("F","G")), ("G","F",exp_hermanos("G","F")),
    ("H","I",exp_hermanos("H","I")), ("I","H",exp_hermanos("I","H")),
    ("H","J",exp_hermanos("H","J")), ("J","H",exp_hermanos("J","H")),
    ("I","J",exp_hermanos("I","J")), ("J","I",exp_hermanos("J","I")),
    ("N","P",exp_hermanos("N","P")), ("P","N",exp_hermanos("P","N")),
    ("N","Q",exp_hermanos("N","Q")), ("Q","N",exp_hermanos("Q","N")),
    ("P","Q",exp_hermanos("P","Q")), ("Q","P",exp_hermanos("Q","P")),
    ("R","S",exp_hermanos("R","S")), ("S","R",exp_hermanos("S","R")),
])
def test_hermanos(a,b,expected):
    assert S.relacion(a,b) == expected

# ---------- PADRES ↔ HIJOS ----------
@pytest.mark.parametrize("a,b,expected", [
    ("A","E",exp_padre("A","E")), ("B","E",exp_padre("B","E")),
    ("A","F",exp_padre("A","F")), ("B","F",exp_padre("B","F")),
    ("A","G",exp_padre("A","G")), ("B","G",exp_padre("B","G")),
    ("C","H",exp_padre("C","H")), ("D","H",exp_padre("D","H")),
    ("C","I",exp_padre("C","I")), ("D","I",exp_padre("D","I")),
    ("C","J",exp_padre("C","J")), ("D","J",exp_padre("D","J")),
    ("E","N",exp_padre("E","N")), ("H","N",exp_padre("H","N")),
    ("E","P",exp_padre("E","P")), ("H","P",exp_padre("H","P")),
    ("E","Q",exp_padre("E","Q")), ("H","Q",exp_padre("H","Q")),
    ("F","R",exp_padre("F","R")), ("K","R",exp_padre("K","R")),
    ("F","S",exp_padre("F","S")), ("K","S",exp_padre("K","S")),
    ("G","O",exp_padre("G","O")), ("L","O",exp_padre("L","O")),
    ("I","T",exp_padre("I","T")), ("M","T",exp_padre("M","T")),
])
def test_padres(a,b,expected):
    assert S.relacion(a,b) == expected

@pytest.mark.parametrize("a,b,expected", [
    ("E","A",exp_hijo("E","A")), ("E","B",exp_hijo("E","B")),
    ("F","A",exp_hijo("F","A")), ("F","B",exp_hijo("F","B")),
    ("G","A",exp_hijo("G","A")), ("G","B",exp_hijo("G","B")),
    ("H","C",exp_hijo("H","C")), ("H","D",exp_hijo("H","D")),
    ("I","C",exp_hijo("I","C")), ("I","D",exp_hijo("I","D")),
    ("J","C",exp_hijo("J","C")), ("J","D",exp_hijo("J","D")),
    ("N","E",exp_hijo("N","E")), ("N","H",exp_hijo("N","H")),
    ("P","E",exp_hijo("P","E")), ("P","H",exp_hijo("P","H")),
    ("Q","E",exp_hijo("Q","E")), ("Q","H",exp_hijo("Q","H")),
    ("R","F",exp_hijo("R","F")), ("R","K",exp_hijo("R","K")),
    ("S","F",exp_hijo("S","F")), ("S","K",exp_hijo("S","K")),
    ("O","G",exp_hijo("O","G")), ("O","L",exp_hijo("O","L")),
    ("T","I",exp_hijo("T","I")), ("T","M",exp_hijo("T","M")),
])
def test_hijos(a,b,expected):
    assert S.relacion(a,b) == expected

# ---------- ABUELOS ↔ NIETOS ----------
@pytest.mark.parametrize("a,b,expected", [
    ("A","N",exp_abuelo("A","N")), ("B","N",exp_abuelo("B","N")),
    ("A","P",exp_abuelo("A","P")), ("B","P",exp_abuelo("B","P")),
    ("A","Q",exp_abuelo("A","Q")), ("B","Q",exp_abuelo("B","Q")),
    ("C","R",exp_abuelo("C","R")), ("D","R",exp_abuelo("D","R")),
    ("C","S",exp_abuelo("C","S")), ("D","S",exp_abuelo("D","S")),
])
def test_abuelos(a,b,expected):
    assert S.relacion(a,b) == expected

@pytest.mark.parametrize("a,b,expected", [
    ("N","A",exp_nieto("N","A")), ("N","B",exp_nieto("N","B")),
    ("P","A",exp_nieto("P","A")), ("P","B",exp_nieto("P","B")),
    ("Q","A",exp_nieto("Q","A")), ("Q","B",exp_nieto("Q","B")),
    ("R","C",exp_nieto("R","C")), ("R","D",exp_nieto("R","D")),
    ("S","C",exp_nieto("S","C")), ("S","D",exp_nieto("S","D")),
])
def test_nietos(a,b,expected):
    assert S.relacion(a,b) == expected

# ---------- SUEGROS ↔ YERNO/NUERA ----------
@pytest.mark.parametrize("a,b,expected", [
    ("A","H",exp_suegro("A","H")), ("B","H",exp_suegro("B","H")),
    ("C","K",exp_suegro("C","K")), ("D","K",exp_suegro("D","K")),
    ("A","L",exp_suegro("A","L")), ("B","L",exp_suegro("B","L")),
    ("C","M",exp_suegro("C","M")), ("D","M",exp_suegro("D","M")),
])
def test_suegros(a,b,expected):
    assert S.relacion(a,b) == expected

@pytest.mark.parametrize("a,b,expected", [
    ("H","A",exp_yerno("H","A")), ("H","B",exp_yerno("H","B")),
    ("K","C",exp_yerno("K","C")), ("K","D",exp_yerno("K","D")),
    ("L","A",exp_yerno("L","A")), ("L","B",exp_yerno("L","B")),
    ("M","C",exp_yerno("M","C")), ("M","D",exp_yerno("M","D")),
])
def test_yernos(a,b,expected):
    assert S.relacion(a,b) == expected

# ---------- TÍOS ↔ SOBRINOS (incluye políticos) ----------
@pytest.mark.parametrize("a,b,expected", [
    ("E","R",exp_tio("E","R")), ("E","S",exp_tio("E","S")),
    ("F","N",exp_tio("F","N")), ("F","P",exp_tio("F","P")), ("F","Q",exp_tio("F","Q")),
    ("G","N",exp_tio("G","N")), ("G","P",exp_tio("G","P")), ("G","Q",exp_tio("G","Q")),
    ("E","O",exp_tio("E","O")), ("F","O",exp_tio("F","O")),
    ("I","N",exp_tio("I","N")), ("I","P",exp_tio("I","P")), ("I","Q",exp_tio("I","Q")),
    ("J","N",exp_tio("J","N")), ("J","P",exp_tio("J","P")), ("J","Q",exp_tio("J","Q")),
    ("H","R",exp_tio("H","R")), ("H","S",exp_tio("H","S")),
    ("K","N",exp_tio("K","N")), ("K","P",exp_tio("K","P")), ("K","Q",exp_tio("K","Q")),
    ("L","N",exp_tio("L","N")), ("L","P",exp_tio("L","P")), ("L","Q",exp_tio("L","Q")),
])
def test_tios(a,b,expected):
    assert S.relacion(a,b) == expected

@pytest.mark.parametrize("a,b,expected", [
    ("R","E",exp_sobrino("R","E")), ("S","E",exp_sobrino("S","E")),
    ("N","F",exp_sobrino("N","F")), ("P","F",exp_sobrino("P","F")), ("Q","F",exp_sobrino("Q","F")),
    ("N","G",exp_sobrino("N","G")), ("P","G",exp_sobrino("P","G")), ("Q","G",exp_sobrino("Q","G")),
    ("O","E",exp_sobrino("O","E")), ("O","F",exp_sobrino("O","F")),
    ("N","I",exp_sobrino("N","I")), ("P","I",exp_sobrino("P","I")), ("Q","I",exp_sobrino("Q","I")),
    ("N","J",exp_sobrino("N","J")), ("P","J",exp_sobrino("P","J")), ("Q","J",exp_sobrino("Q","J")),
    ("R","H",exp_sobrino("R","H")), ("S","H",exp_sobrino("S","H")),
    ("N","K",exp_sobrino("N","K")), ("P","K",exp_sobrino("P","K")), ("Q","K",exp_sobrino("Q","K")),
    ("N","L",exp_sobrino("N","L")), ("P","L",exp_sobrino("P","L")), ("Q","L",exp_sobrino("Q","L")),
])
def test_sobrinos(a,b,expected):
    assert S.relacion(a,b) == expected

# ---------- CUÑADOS (solo directos; sin segundo grado) ----------
@pytest.mark.parametrize("a,b,expected", [
    ("E","K",exp_cunados("E","K")), ("K","E",exp_cunados("K","E")),
    ("E","L",exp_cunados("E","L")), ("L","E",exp_cunados("L","E")),
    ("E","I",exp_cunados("E","I")), ("I","E",exp_cunados("I","E")),
    ("E","J",exp_cunados("E","J")), ("J","E",exp_cunados("J","E")),
    ("G","I",exp_cunados("G","I")), ("I","G",exp_cunados("I","G")),
    # Ojo: aquí ya NO probamos H-L ni H-K (cuñados de segundo grado)
])
def test_cunados(a,b,expected):
    assert S.relacion(a,b) == expected

# ---------- PRIMOS ----------
@pytest.mark.parametrize("a,b,expected", [
    ("N","R",exp_primos("N","R")), ("R","N",exp_primos("R","N")),
    ("N","S",exp_primos("N","S")), ("S","N",exp_primos("S","N")),
    ("P","R",exp_primos("P","R")), ("R","P",exp_primos("R","P")),
    ("P","S",exp_primos("P","S")), ("S","P",exp_primos("S","P")),
    ("Q","R",exp_primos("Q","R")), ("R","Q",exp_primos("R","Q")),
    ("Q","S",exp_primos("Q","S")), ("S","Q",exp_primos("S","Q")),
    ("N","O",exp_primos("N","O")), ("O","N",exp_primos("O","N")),
    ("P","O",exp_primos("P","O")), ("O","P",exp_primos("O","P")),
    ("Q","O",exp_primos("Q","O")), ("O","Q",exp_primos("O","Q")),
    ("N","T",exp_primos("N","T")), ("T","N",exp_primos("T","N")),
    ("P","T",exp_primos("P","T")), ("T","P",exp_primos("T","P")),
    ("Q","T",exp_primos("Q","T")), ("T","Q",exp_primos("T","Q")),
])
def test_primos(a,b,expected):
    assert S.relacion(a,b) == expected

# ---------- Permite ejecutar directo con Python ----------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
