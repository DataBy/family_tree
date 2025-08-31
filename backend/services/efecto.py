from datetime import date
from typing import List, Dict

# ----------------------------------------
# Helpers
# ----------------------------------------
def edad_actual(persona: Dict) -> int | None:
    """Devuelve edad actual a partir de fecha de nacimiento YYYY-MM-DD."""
    try:
        if not persona.get("fecha_nacimiento"):
            return None
        y, m, d = map(int, persona["fecha_nacimiento"][:10].split("-"))
        today = date.today()
        return today.year - y - ((today.month, today.day) < (m, d))
    except Exception:
        return None


def es_menor(persona: Dict) -> bool:
    e = edad_actual(persona)
    return e is not None and e < 18


def _full(p: Dict) -> str:
    return p.get("nombre_completo") or f"{p.get('nombre','')} {p.get('apellidos','')}".strip()


# ----------------------------------------
# Reglas de efectos colaterales
# ----------------------------------------

def asignar_tutores(menor: Dict, posibles_tutores: List[Dict]) -> List[Dict]:
    """
    Elige todos los tutores posibles para un menor según prioridad:
    1. Hermanos mayores de 18
    2. Tíos/tías
    3. Abuelos
    4. Cuñados/as de los padres
    5. Otros adultos de la familia
    """
    candidatos: List[Dict] = []

    def es_adulto(p: Dict) -> bool:
        return (edad_actual(p) or 0) >= 18

    # 1. Hermanos mayores
    hermanos = [t for t in posibles_tutores if "hermano" in (t.get("rol") or "").lower() and es_adulto(t)]
    candidatos.extend(hermanos)

    # 2. Tíos/tías
    tios = [t for t in posibles_tutores if ("tio" in (t.get("rol") or "").lower() or "tia" in (t.get("rol") or "").lower()) and es_adulto(t)]
    candidatos.extend(tios)

    # 3. Abuelos
    abuelos = [t for t in posibles_tutores if ("abuelo" in (t.get("rol") or "").lower() or "abuela" in (t.get("rol") or "").lower()) and es_adulto(t)]
    candidatos.extend(abuelos)

    # 4. Cuñados/as de los padres
    cunados = [t for t in posibles_tutores if "cuñado" in (t.get("rol") or "").lower() or "cuñada" in (t.get("rol") or "").lower()]
    candidatos.extend(cunados)

    # 5. Otros adultos
    otros = [t for t in posibles_tutores if es_adulto(t) and t not in candidatos]
    candidatos.extend(otros)

    return candidatos


def aplicar_tutores_en_familia(matriz: list[list[list[Dict]]]) -> None:
    """
    Si ambos padres de un menor mueren, asigna todos los posibles tutores en orden de prioridad.
    """
    for fila in matriz:
        for celda in fila:
            for p in celda:
                if es_menor(p):
                    madre_viva = not bool(p.get("madre_defuncion"))
                    padre_vivo = not bool(p.get("padre_defuncion"))
                    if not madre_viva and not padre_vivo:
                        # Todos los demás adultos de la familia menos el menor
                        posibles = [x for row in matriz for cell in row for x in cell if x != p]
                        tutores = asignar_tutores(p, posibles)
                        if tutores:
                            # Guardamos la lista completa
                            p["tutores_legales"] = [_full(t) for t in tutores]


                            

def aplicar_viudez(persona: Dict) -> None:
    """
    Si queda viuda/o, cambia estado y baja chance de nueva unión.
    """
    if persona.get("estado_civil", "").lower().startswith("viud"):
        persona["prob_union"] = max(0, persona.get("prob_union", 100) - 30)


def aplicar_solteria_prolongada(persona: Dict) -> None:
    """
    Si pasa más de 10 años soltera/o, baja salud emocional y esperanza de vida.
    """
    if persona.get("estado_civil", "").lower().startswith("solter"):
        anios = (date.today().year - persona.get("anio_solteria", date.today().year))
        if anios >= 10:
            persona["salud_emocional"] = persona.get("salud_emocional", 100) - 20
            persona["esperanza_vida"] = persona.get("esperanza_vida", 80) - 5


def procesar_colaterales(matriz: list[list[list[Dict]]]) -> None:
    """
    Procesa todos los efectos colaterales sobre la familia.
    """
    aplicar_tutores_en_familia(matriz)
    for fila in matriz:
        for celda in fila:
            for p in celda:
                aplicar_viudez(p)
                aplicar_solteria_prolongada(p)
