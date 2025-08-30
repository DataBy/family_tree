# backend/services/cumpleaños.py
from __future__ import annotations
from datetime import date, datetime
from typing import Iterator, Dict, Any, List, Optional, TypedDict, NotRequired
from . import db  # Importar el módulo db existente
import logging

logger = logging.getLogger(__name__)

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
    nombre_completo: str


class InfoCumpleanos(TypedDict):
    nombre: str
    cedula: str
    fecha_nacimiento: str
    fecha_defuncion: str
    fallecido: bool
    cumple_hoy: bool
    error: NotRequired[str]


class ResumenCumpleanosFamilia(TypedDict):
    familia: str
    hoy: str
    cumple_hoy: List[InfoCumpleanos]


class ResumenCumpleanosGlobal(TypedDict):
    hoy: str
    familias: List[ResumenCumpleanosFamilia]
    todos_cumple_hoy: List[InfoCumpleanos]

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


def obtener_fecha_actual() -> date:
    """Función auxiliar para facilitar testing."""
    return date.today()


# -----------------------------
# Helpers sobre la estructura de db.py
# -----------------------------
def _personas_en_familia(nombre_familia: str) -> Iterator[PersonaDict]:
    """Itera sobre todas las personas de una familia usando la estructura de db.py"""
    matriz = db.obtener_matriz(nombre_familia) or []
    for fila in matriz:
        for celda in fila:
            for p in celda:
                yield p  # type: ignore[return-value]


def _nombre_completo(p: Dict[str, Any]) -> str:
    # Adaptado para trabajar con la estructura de db.py
    nombre_completo = p.get("nombre_completo")
    if nombre_completo:
        return nombre_completo
    return f"{p.get('nombre','').strip()} {p.get('apellidos','').strip()}".strip()


def _fecha_nac(p: Dict[str, Any]) -> Optional[date]:
    raw = (p.get("fecha_nacimiento") or "").strip()
    if not raw:
        return None
    try:
        return _parse_fecha(raw)
    except ValueError:
        logger.warning(f"Fecha de nacimiento inválida para persona: {p}")
        return None


def _fecha_def(p: Dict[str, Any]) -> Optional[date]:
    raw = (p.get("fecha_defuncion") or "").strip()
    if not raw:
        return None
    try:
        return _parse_fecha(raw)
    except ValueError:
        logger.warning(f"Fecha de defunción inválida para persona: {p}")
        return None


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


def _info_cumpleanos_persona(p: PersonaDict, hoy: date) -> InfoCumpleanos:
    """
    Verifica si una persona cumple años hoy.
    """
    f_nac = _fecha_nac(p)
    f_def = _fecha_def(p)
    fallecido = f_def is not None

    # Validaciones lógicas básicas
    err = _validar_logica_fechas(f_nac, f_def)

    out: InfoCumpleanos = {
        "nombre": _nombre_completo(p),
        "cedula": p.get("cedula") or "",
        "fecha_nacimiento": p.get("fecha_nacimiento") or "",
        "fecha_defuncion": p.get("fecha_defuncion") or "",
        "fallecido": fallecido,
        "cumple_hoy": False,
    }

    # Si hay error lógico serio, devolvemos el error.
    if err:
        logger.warning(f"Persona con error lógico de fechas: {err} - {p}")
        out["error"] = err
        return out

    # Solo verificar cumpleaños para personas vivas
    if not fallecido and f_nac:
        # Verificar si cumple años hoy (mismo mes y día)
        if f_nac.month == hoy.month and f_nac.day == hoy.day:
            out["cumple_hoy"] = True

    return out


def cumpleanos_hoy_familia(nombre_familia: str, hoy: Optional[date] = None) -> ResumenCumpleanosFamilia:
    """Obtiene personas que cumplen años hoy en una familia específica"""
    if not db.existe_familia(nombre_familia):
        raise ValueError(f"La familia '{nombre_familia}' no existe")
    
    hoy = hoy or obtener_fecha_actual()
    cumple_hoy: List[InfoCumpleanos] = []

    for p in _personas_en_familia(nombre_familia):
        info = _info_cumpleanos_persona(p, hoy)
        if info["cumple_hoy"]:
            cumple_hoy.append(info)

    return {
        "familia": nombre_familia,
        "hoy": hoy.isoformat(),
        "cumple_hoy": cumple_hoy,
    }


# -----------------------------
# Deduplicación para resumen global
# -----------------------------
def _dedup_por_cedula(items: List[InfoCumpleanos]) -> List[InfoCumpleanos]:
    """
    Dedup por 'cedula' (si no hay, usa 'nombre' como fallback).
    Evita doble conteo si una persona aparece en más de una celda.
    """
    seen = set()
    out = []
    for item in items:
        key = item.get("cedula") or item.get("nombre")
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def cumpleanos_hoy_global(hoy: Optional[date] = None) -> ResumenCumpleanosGlobal:
    """Obtiene todas las personas que cumplen años hoy en todas las familias"""
    hoy = hoy or obtener_fecha_actual()
    data: ResumenCumpleanosGlobal = {
        "hoy": hoy.isoformat(),
        "familias": [],
        "todos_cumple_hoy": [],
    }
    
    for fam in db.listar_familias():
        try:
            r = cumpleanos_hoy_familia(fam, hoy)
            data["familias"].append(r)
            data["todos_cumple_hoy"].extend(r["cumple_hoy"])
        except Exception as e:
            logger.error(f"Error procesando familia {fam}: {e}")
            continue

    # Eliminar duplicados
    data["todos_cumple_hoy"] = _dedup_por_cedula(data["todos_cumple_hoy"])
    
    return data


# -----------------------------
# Funciones específicas para la simulación de vida
# -----------------------------
def obtener_cumpleaneros_hoy(nombre_familia: str, hoy: Optional[date] = None) -> List[Dict[str, Any]]:
    """Obtiene personas que cumplen años hoy (compatibilidad con simulación)"""
    hoy = hoy or obtener_fecha_actual()
    cumpleanieros = []
    
    try:
        resumen = cumpleanos_hoy_familia(nombre_familia, hoy)
        cumpleanieros = resumen["cumple_hoy"]
    except Exception as e:
        logger.error(f"Error obteniendo cumpleañeros de {nombre_familia}: {e}")
    
    return cumpleanieros


def verificar_cumpleanos_hoy(nombre_familia: str, hoy: Optional[date] = None) -> Dict[str, Any]:
    """Verifica si hay cumpleaños hoy en una familia"""
    hoy = hoy or obtener_fecha_actual()
    
    try:
        resumen = cumpleanos_hoy_familia(nombre_familia, hoy)
        return {
            "familia": nombre_familia,
            "hoy": hoy.isoformat(),
            "hay_cumpleaneros": len(resumen["cumple_hoy"]) > 0,
            "cumpleaneros": resumen["cumple_hoy"],
            "cantidad": len(resumen["cumple_hoy"])
        }
    except Exception as e:
        logger.error(f"Error verificando cumpleaños de {nombre_familia}: {e}")
        return {"error": str(e)}