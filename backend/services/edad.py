# backend/services/edad.py
from __future__ import annotations
from datetime import date, datetime
from typing import Iterator, Dict, Any, List, Optional, TypedDict
from . import db  # listar_familias(), existe_familia(), obtener_matriz()

# Formatos de fecha aceptados (en orden de intento)
_FORMATOS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y")


# -----------------------------
# Tipos (opcional, ayuda a IDE)
# -----------------------------
class PersonaDict(TypedDict, total=False):
    nombre: str
    apellidos: str
    cedula: str
    fecha_nacimiento: str
    fecha_defuncion: str
    edad_calculada: int
    edad_actualizada: str
    nacimiento_iso: str
    defuncion_iso: str


# -----------------------------
# Helpers de fecha y parseo
# -----------------------------
def _parse_fecha(s: str) -> date:
    s = (s or "").strip()
    for fmt in _FORMATOS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Fecha inválida: {s!r}")


def _safe_bday_year(nac: date, year: int) -> date:
    """Devuelve el cumpleaños de ese año; si es 29-feb en no-bisiesto => 28-feb."""
    try:
        return nac.replace(year=year)
    except ValueError:
        return date(year, 2, 28)


def _edad_en(nac: date, ref: date) -> int:
    edad = ref.year - nac.year
    if (ref.month, ref.day) < (nac.month, nac.day):
        edad -= 1
    return edad


def _validar_logica_fechas(f_nac: Optional[date], f_def: Optional[date]) -> Optional[str]:
    """Valida coherencia temporal básica. Retorna código de error o None."""
    if not f_nac:
        return "SIN_FECHA_NAC"
    hoy = date.today()
    if f_nac > hoy:
        return "NACIMIENTO_FUTURO"
    if f_def and f_def < f_nac:
        return "DEF_ANTES_NAC"
    return None


# -----------------------------
# Helpers sobre la estructura
# -----------------------------
def _personas_en_familia(nombre_familia: str) -> Iterator[PersonaDict]:
    matriz = db.obtener_matriz(nombre_familia) or []
    for fila in matriz:
        for celda in fila:
            for p in celda:
                # 'p' es el dict REAL dentro de la matriz -> mutaciones son in-place
                yield p  # type: ignore[return-value]


def _nombre_completo(p: Dict[str, Any]) -> str:
    return f"{p.get('nombre','').strip()} {p.get('apellidos','').strip()}".strip()


def _fecha_nac(p: Dict[str, Any]) -> Optional[date]:
    raw = (p.get("fecha_nacimiento") or "").strip()
    if not raw:
        return None
    try:
        return _parse_fecha(raw)
    except ValueError:
        return None


def _fecha_def(p: Dict[str, Any]) -> Optional[date]:
    raw = (p.get("fecha_defuncion") or "").strip()
    if not raw:
        return None
    try:
        return _parse_fecha(raw)
    except ValueError:
        return None


def _res_persona(p: PersonaDict, hoy: date) -> Dict[str, Any]:
    """
    Calcula datos de edad/cumple y, como opción B, ACTUALIZA IN-MEMORY:
      - p['edad_calculada'] = edad (vivo: al día; fallecido: al fallecer)
      - p['edad_actualizada'] = hoy.isoformat()
      - p['nacimiento_iso'] y p['defuncion_iso'] si son válidas (opcional, útil para auditoría)
    """
    f_nac = _fecha_nac(p)
    f_def = _fecha_def(p)
    fallecido = f_def is not None

    # Validaciones lógicas básicas
    err = _validar_logica_fechas(f_nac, f_def)

    out: Dict[str, Any] = {
        "nombre": _nombre_completo(p),
        "cedula": p.get("cedula") or "",
        "fecha_nacimiento": p.get("fecha_nacimiento") or "",
        "fecha_defuncion": p.get("fecha_defuncion") or "",
        "fallecido": fallecido,
        "edad": None,              # vivo: edad actual; fallecido: edad al fallecer
        "cumple_hoy": False,       # solo vivos
        "dias_para_cumple": None,  # solo vivos
        # Campo nuevo para UI: fecha del próximo cumple (solo vivos)
        "proximo_cumple": None,
    }

    # Si hay error lógico serio, no persistimos edad; devolvemos el error.
    if err:
        out["error"] = err
        return out

    # Persistimos fechas normalizadas útiles (si existen)
    if f_nac:
        p["nacimiento_iso"] = f_nac.isoformat()
    if f_def:
        p["defuncion_iso"] = f_def.isoformat()

    # Edad (al día si vivo; a la fecha de defunción si fallecido)
    ref = f_def if fallecido else hoy
    edad_calc = _edad_en(f_nac, ref) if f_nac else None
    out["edad"] = edad_calc

    # --- Opción B: persistir en el dict 'p' directamente (in-memory) ---
    if edad_calc is not None:
        p["edad_calculada"] = edad_calc
        p["edad_actualizada"] = hoy.isoformat()

    # Cumpleaños (solo vivos)
    if not fallecido and f_nac:
        cumple_este_anio = _safe_bday_year(f_nac, hoy.year)
        if cumple_este_anio == hoy:
            out["cumple_hoy"] = True
            out["dias_para_cumple"] = 0
            out["proximo_cumple"] = hoy.isoformat()
        else:
            proximo = cumple_este_anio if cumple_este_anio > hoy else _safe_bday_year(f_nac, hoy.year + 1)
            out["dias_para_cumple"] = (proximo - hoy).days
            out["proximo_cumple"] = proximo.isoformat()

    return out


def resumen_familia(nombre_familia: str, hoy: Optional[date] = None) -> Dict[str, Any]:
    hoy = hoy or date.today()
    vivos: List[Dict[str, Any]] = []
    fallecidos: List[Dict[str, Any]] = []

    for p in _personas_en_familia(nombre_familia):
        r = _res_persona(p, hoy)
        (fallecidos if r["fallecido"] else vivos).append(r)

    cumple_hoy = [r for r in vivos if r["cumple_hoy"]]
    proximos = sorted(
        [r for r in vivos if isinstance(r["dias_para_cumple"], int) and r["dias_para_cumple"] > 0],
        key=lambda x: x["dias_para_cumple"]
    )
    proximos_7  = [r for r in proximos if r["dias_para_cumple"] <= 7]
    proximos_30 = [r for r in proximos if r["dias_para_cumple"] <= 30]

    return {
        "familia": nombre_familia,
        "hoy": hoy.isoformat(),
        "vivos": vivos,
        "fallecidos": fallecidos,
        "cumple_hoy": cumple_hoy,
        "proximos_7": proximos_7,
        "proximos_30": proximos_30,
    }


# -----------------------------
# Deduplicación para resumen global
# -----------------------------
def _dedup_por_cedula(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Dedup por 'cedula' (si no hay, usa 'nombre' como fallback).
    Evita doble conteo si una persona aparece en más de una celda.
    """
    seen = set()
    out = []
    for r in items:
        key = r.get("cedula") or r.get("nombre")
        if key and key not in seen:
            seen.add(key)
            out.append(r)
    return out


def resumen_global(hoy: Optional[date] = None) -> Dict[str, Any]:
    hoy = hoy or date.today()
    data = {
        "hoy": hoy.isoformat(),
        "familias": [],
        "cumple_hoy": [],
        "proximos_7": [],
        "proximos_30": [],
    }
    for fam in db.listar_familias():
        r = resumen_familia(fam, hoy)
        data["familias"].append(r)
        data["cumple_hoy"].extend(r["cumple_hoy"])
        data["proximos_7"].extend(r["proximos_7"])
        data["proximos_30"].extend(r["proximos_30"])

    # Dedup antes de ordenar
    data["cumple_hoy"]  = _dedup_por_cedula(data["cumple_hoy"])
    data["proximos_7"]  = _dedup_por_cedula(data["proximos_7"])
    data["proximos_30"] = _dedup_por_cedula(data["proximos_30"])

    # Ordenar por cercanía de cumpleaños
    data["proximos_7"]  = sorted(data["proximos_7"],  key=lambda x: x["dias_para_cumple"])
    data["proximos_30"] = sorted(data["proximos_30"], key=lambda x: x["dias_para_cumple"])
    return data# backend/services/edad.py
from __future__ import annotations
from datetime import date, datetime
from typing import Iterator, Dict, Any, List, Optional, TypedDict
from . import db  # listar_familias(), existe_familia(), obtener_matriz()

# Formatos de fecha aceptados (en orden de intento)
_FORMATOS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y")


# -----------------------------
# Tipos (opcional, ayuda a IDE)
# -----------------------------
class PersonaDict(TypedDict, total=False):
    nombre: str
    apellidos: str
    cedula: str
    fecha_nacimiento: str
    fecha_defuncion: str
    edad_calculada: int
    edad_actualizada: str
    nacimiento_iso: str
    defuncion_iso: str


# -----------------------------
# Helpers de fecha y parseo
# -----------------------------
def _parse_fecha(s: str) -> date:
    s = (s or "").strip()
    for fmt in _FORMATOS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Fecha inválida: {s!r}")


def _safe_bday_year(nac: date, year: int) -> date:
    """Devuelve el cumpleaños de ese año; si es 29-feb en no-bisiesto => 28-feb."""
    try:
        return nac.replace(year=year)
    except ValueError:
        return date(year, 2, 28)


def _edad_en(nac: date, ref: date) -> int:
    edad = ref.year - nac.year
    if (ref.month, ref.day) < (nac.month, nac.day):
        edad -= 1
    return edad


def _validar_logica_fechas(f_nac: Optional[date], f_def: Optional[date]) -> Optional[str]:
    """Valida coherencia temporal básica. Retorna código de error o None."""
    if not f_nac:
        return "SIN_FECHA_NAC"
    hoy = date.today()
    if f_nac > hoy:
        return "NACIMIENTO_FUTURO"
    if f_def and f_def < f_nac:
        return "DEF_ANTES_NAC"
    return None


# -----------------------------
# Helpers sobre la estructura
# -----------------------------
def _personas_en_familia(nombre_familia: str) -> Iterator[PersonaDict]:
    matriz = db.obtener_matriz(nombre_familia) or []
    for fila in matriz:
        for celda in fila:
            for p in celda:
                # 'p' es el dict REAL dentro de la matriz -> mutaciones son in-place
                yield p  # type: ignore[return-value]


def _nombre_completo(p: Dict[str, Any]) -> str:
    return f"{p.get('nombre','').strip()} {p.get('apellidos','').strip()}".strip()


def _fecha_nac(p: Dict[str, Any]) -> Optional[date]:
    raw = (p.get("fecha_nacimiento") or "").strip()
    if not raw:
        return None
    try:
        return _parse_fecha(raw)
    except ValueError:
        return None


def _fecha_def(p: Dict[str, Any]) -> Optional[date]:
    raw = (p.get("fecha_defuncion") or "").strip()
    if not raw:
        return None
    try:
        return _parse_fecha(raw)
    except ValueError:
        return None


def _res_persona(p: PersonaDict, hoy: date) -> Dict[str, Any]:
    """
    Calcula datos de edad/cumple y, como opción B, ACTUALIZA IN-MEMORY:
      - p['edad_calculada'] = edad (vivo: al día; fallecido: al fallecer)
      - p['edad_actualizada'] = hoy.isoformat()
      - p['nacimiento_iso'] y p['defuncion_iso'] si son válidas (opcional, útil para auditoría)
    """
    f_nac = _fecha_nac(p)
    f_def = _fecha_def(p)
    fallecido = f_def is not None

    # Validaciones lógicas básicas
    err = _validar_logica_fechas(f_nac, f_def)

    out: Dict[str, Any] = {
        "nombre": _nombre_completo(p),
        "cedula": p.get("cedula") or "",
        "fecha_nacimiento": p.get("fecha_nacimiento") or "",
        "fecha_defuncion": p.get("fecha_defuncion") or "",
        "fallecido": fallecido,
        "edad": None,              # vivo: edad actual; fallecido: edad al fallecer
        "cumple_hoy": False,       # solo vivos
        "dias_para_cumple": None,  # solo vivos
        # Campo nuevo para UI: fecha del próximo cumple (solo vivos)
        "proximo_cumple": None,
    }

    # Si hay error lógico serio, no persistimos edad; devolvemos el error.
    if err:
        out["error"] = err
        return out

    # Persistimos fechas normalizadas útiles (si existen)
    if f_nac:
        p["nacimiento_iso"] = f_nac.isoformat()
    if f_def:
        p["defuncion_iso"] = f_def.isoformat()

    # Edad (al día si vivo; a la fecha de defunción si fallecido)
    ref = f_def if fallecido else hoy
    edad_calc = _edad_en(f_nac, ref) if f_nac else None
    out["edad"] = edad_calc

    # --- Opción B: persistir en el dict 'p' directamente (in-memory) ---
    if edad_calc is not None:
        p["edad_calculada"] = edad_calc
        p["edad_actualizada"] = hoy.isoformat()

    # Cumpleaños (solo vivos)
    if not fallecido and f_nac:
        cumple_este_anio = _safe_bday_year(f_nac, hoy.year)
        if cumple_este_anio == hoy:
            out["cumple_hoy"] = True
            out["dias_para_cumple"] = 0
            out["proximo_cumple"] = hoy.isoformat()
        else:
            proximo = cumple_este_anio if cumple_este_anio > hoy else _safe_bday_year(f_nac, hoy.year + 1)
            out["dias_para_cumple"] = (proximo - hoy).days
            out["proximo_cumple"] = proximo.isoformat()

    return out


def resumen_familia(nombre_familia: str, hoy: Optional[date] = None) -> Dict[str, Any]:
    hoy = hoy or date.today()
    vivos: List[Dict[str, Any]] = []
    fallecidos: List[Dict[str, Any]] = []

    for p in _personas_en_familia(nombre_familia):
        r = _res_persona(p, hoy)
        (fallecidos if r["fallecido"] else vivos).append(r)

    cumple_hoy = [r for r in vivos if r["cumple_hoy"]]
    proximos = sorted(
        [r for r in vivos if isinstance(r["dias_para_cumple"], int) and r["dias_para_cumple"] > 0],
        key=lambda x: x["dias_para_cumple"]
    )
    proximos_7  = [r for r in proximos if r["dias_para_cumple"] <= 7]
    proximos_30 = [r for r in proximos if r["dias_para_cumple"] <= 30]

    return {
        "familia": nombre_familia,
        "hoy": hoy.isoformat(),
        "vivos": vivos,
        "fallecidos": fallecidos,
        "cumple_hoy": cumple_hoy,
        "proximos_7": proximos_7,
        "proximos_30": proximos_30,
    }


# -----------------------------
# Deduplicación para resumen global
# -----------------------------
def _dedup_por_cedula(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Dedup por 'cedula' (si no hay, usa 'nombre' como fallback).
    Evita doble conteo si una persona aparece en más de una celda.
    """
    seen = set()
    out = []
    for r in items:
        key = r.get("cedula") or r.get("nombre")
        if key and key not in seen:
            seen.add(key)
            out.append(r)
    return out


def resumen_global(hoy: Optional[date] = None) -> Dict[str, Any]:
    hoy = hoy or date.today()
    data = {
        "hoy": hoy.isoformat(),
        "familias": [],
        "cumple_hoy": [],
        "proximos_7": [],
        "proximos_30": [],
    }
    for fam in db.listar_familias():
        r = resumen_familia(fam, hoy)
        data["familias"].append(r)
        data["cumple_hoy"].extend(r["cumple_hoy"])
        data["proximos_7"].extend(r["proximos_7"])
        data["proximos_30"].extend(r["proximos_30"])

    # Dedup antes de ordenar
    data["cumple_hoy"]  = _dedup_por_cedula(data["cumple_hoy"])
    data["proximos_7"]  = _dedup_por_cedula(data["proximos_7"])
    data["proximos_30"] = _dedup_por_cedula(data["proximos_30"])

    # Ordenar por cercanía de cumpleaños
    data["proximos_7"]  = sorted(data["proximos_7"],  key=lambda x: x["dias_para_cumple"])
    data["proximos_30"] = sorted(data["proximos_30"], key=lambda x: x["dias_para_cumple"])
    return data