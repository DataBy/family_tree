# backend/services/gestor.py
from __future__ import annotations

from datetime import date
import threading
import random
from typing import Callable, Optional, Dict, Any, List
import logging

log = logging.getLogger(__name__)

from . import db  # usa tu db.py (misma carpeta services)

Cambio = Dict[str, Any]  # {"tipo": "cumple|fallecimiento|union|nacimiento", ...}

# ===========================================================
# Helpers generales
# ===========================================================

def _add_years_safe(d: date, years: int) -> date:
    """Suma años manejando 29/Feb."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # 29-feb -> 28-feb del año destino
        return d.replace(month=2, day=28, year=d.year + years)

def _personas_en_familia(nombre_familia: str):
    """Itera personas válidas (descarta celdas vacías y registros incompletos)."""
    m = db.obtener_matriz(nombre_familia) or []
    for fila in m:
        for celda in fila:
            for p in celda:
                if not p or not isinstance(p, dict):
                    continue
                if not (p.get("nombre") or p.get("apellidos")):
                    continue
                yield p

def _vivas(personas):
    for p in personas:
        if not p.get("fecha_defuncion"):
            yield p

def _nombre_completo(p: dict) -> str:
    return (
        p.get("nombre_completo")
        or f"{p.get('nombre','').strip()} {p.get('apellidos','').strip()}".strip()
    )

def _edad_simulada(p: dict, ref: date) -> Optional[int]:
    """Calcula edad por fecha_nacimiento vs ref si no hay 'edad'. Si hay 'edad', úsala."""
    if "edad" in p and isinstance(p["edad"], (int, float)):
        try:
            return int(p["edad"])
        except Exception:
            return None
    try:
        y, m, d = map(int, (p.get("fecha_nacimiento") or "0000-01-01").split("-"))
        e = ref.year - y - ((ref.month, ref.day) < (m, d))
        return e
    except Exception:
        return None

def _prob_muerte(edad: Optional[int]) -> float:
    """Probabilidad simple, creciente con la edad (ajustable).
    A partir de los 100 años la muerte es segura.
    """
    if edad is None:
        return 0.001
    if edad < 1:
        return 0.001
    if edad < 40:
        return 0.003
    if edad < 60:
        return 0.005
    if edad < 75:
        return 0.015
    if edad < 85:
        return 0.04
    if edad < 100:
        return 0.08
    return 1.0  # Nadie vive más de 100 años

def _primer_apellido(apellidos: str) -> str:
    return (apellidos or "").split()[0] if apellidos else ""

def _apellidos_hijo(padre: dict, madre: dict) -> str:
    return f"{_primer_apellido(padre.get('apellidos',''))} {_primer_apellido(madre.get('apellidos',''))}".strip()

def _genero_opuesto(g1: str, g2: str) -> bool:
    if not g1 or not g2:
        return False
    return (g1.lower().startswith("f") and g2.lower().startswith("m")) or (
        g1.lower().startswith("m") and g2.lower().startswith("f")
    )

def _edad_por_fecha_iso(fecha_iso: str, ref: date) -> Optional[int]:
    """Edad a partir de fecha ISO YYYY-MM-DD vs ref."""
    try:
        y, m, d = map(int, (fecha_iso or "0000-01-01").split("-"))
        return ref.year - y - ((ref.month, ref.day) < (m, d))
    except Exception:
        return None


# ===========================================================
# Clase principal
# ===========================================================

class GestorEventos:
    """
    Simulador:
      - Cada tick (10s por defecto) avanza 1 año 'virtual' para TODAS las personas vivas (p['edad'] += 1).
      - Muertes aleatorias (según edad).
      - Uniones (parejas M/F) con compatibilidad suficiente.
      - Nacimientos en parejas: bebé va a fila (fila_pareja+1) y misma columna de la pareja; cédula autogenerada.
    """

    def __init__(
        self,
        tick_seg: int = 10,
        anios_por_tick: int = 1,
        rng_seed: Optional[int] = None,
        on_change: Optional[Callable[[List[Cambio]], None]] = None,
        max_uniones_por_familia_por_tick: int = 1,
        prob_nacimiento_por_pareja_por_tick: float = 0.25,
    ):
        self.tick_seg = tick_seg
        self.anios_por_tick = anios_por_tick
        self.on_change = on_change
        self._timer: Optional[threading.Timer] = None
        self._running = False
        self.hoy: date = date.today()
        self.rng = random.Random(rng_seed)
        self.max_uniones_por_familia_por_tick = max_uniones_por_familia_por_tick
        self.prob_nacimiento_por_pareja_por_tick = prob_nacimiento_por_pareja_por_tick

        # Listas de nombres aleatorios
        self.nombres_m = [
            "Carlos","Luis","Mateo","Diego","Gabriel","Bruno",
            "Iker","Tomás","Daniel","Lucas","Nicolás"
        ]
        self.nombres_f = [
            "María","Ana","Sofía","Valeria","Emma","Camila",
            "Lucía","Sara","Zoe","Luna","Mía"
        ]

    # ---------------- Ciclo de vida ----------------
    def start(self):
        if self._running:
            return
        self._running = True
        self._programar_siguiente_tick()

    def stop(self):
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def step_once(self) -> List[Cambio]:
        """Ejecuta un tick manualmente (útil para pruebas o botones en UI)."""
        return self._tick()

    def _programar_siguiente_tick(self):
        if not self._running:
            return
        self._timer = threading.Timer(self.tick_seg, self._tick_and_reschedule)
        self._timer.daemon = True
        self._timer.start()

    def _tick_and_reschedule(self):
        try:
            self._tick()
        finally:
            self._programar_siguiente_tick()

    # ===========================================================
    # Lógica principal del simulador
    # ===========================================================

    def _tick(self) -> List[Cambio]:
        eventos: List[Cambio] = []

        # Avanza el "hoy" simulado
        self.hoy = _add_years_safe(self.hoy, self.anios_por_tick)

        # ---------------------------------------------------
        # 1) Cumpleaños
        # ---------------------------------------------------
        for fam in db.listar_familias():
            for p in _vivas(_personas_en_familia(fam)):
                e = _edad_simulada(p, self.hoy)
                if e is None:
                    p["edad"] = self.anios_por_tick
                else:
                    p["edad"] = int(e) + self.anios_por_tick
                eventos.append({
                    "tipo": "cumple",
                    "familia": fam,
                    "cedula": p.get("cedula",""),
                    "nombre": _nombre_completo(p),
                    "nueva_edad": p["edad"],
                })

        # ---------------------------------------------------
        # 2) Fallecimientos
        # ---------------------------------------------------
        from . import efecto  # asegúrate de importar arriba del archivo

        for fam in db.listar_familias():
            matriz = db.obtener_matriz(fam) or []
            for p in _vivas(_personas_en_familia(fam)):
                edad = _edad_simulada(p, self.hoy)
                if self.rng.random() < _prob_muerte(edad):
                    # Marcar fecha de defunción
                    p["fecha_defuncion"] = self.hoy.isoformat()

                    # Propagar defunción a los hijos
                    for fila in matriz:
                        for celda in fila:
                            for hijo in celda:
                                if hijo.get("madre_cedula") == p.get("cedula"):
                                    hijo["madre_defuncion"] = True
                                if hijo.get("padre_cedula") == p.get("cedula"):
                                    hijo["padre_defuncion"] = True

                    eventos.append({
                        "tipo": "fallecimiento",
                        "familia": fam,
                        "cedula": p.get("cedula", ""),
                        "nombre": _nombre_completo(p),
                        "fecha": self.hoy.isoformat(),
                    })

            # Después de procesar muertes en esta familia → aplicar efectos colaterales
            efecto.procesar_colaterales(matriz)


        # ---------------------------------------------------
        # 3) Nacimientos automáticos (solo parejas existentes en fila 2)
        #     - Usa probabilidad self.prob_nacimiento_por_pareja_por_tick
        #     - Máximo 2 nacimientos extra por pareja (por tick)
        # ---------------------------------------------------
        eventos.extend(self._auto_nacimientos_tick(max_bebes_por_pareja=2))

        # ---------------------------------------------------
        # Notificación a la UI
        # ---------------------------------------------------
        if self.on_change:
            try:
                self.on_change(eventos)
            except Exception:
                pass

        return eventos

    # ===========================================================
    # Nacimientos automáticos (helpers)
    # ===========================================================

    def _parejas_validas_en_fila2(self, familia: str) -> List[Dict[str, Any]]:
        """
        Parejas 'fértiles' en fila 2:
          - Celda con >=2 dicts (pareja)
          - Ambos vivos
          - Se identifica madre por genero y está 18..45 (edad simulada contra self.hoy)
        """
        m = db.obtener_matriz(familia) or []
        out = []
        if len(m) <= 2:
            return out
        for col_idx, celda in enumerate(m[2]):
            if len(celda) < 2 or not all(isinstance(x, dict) for x in celda[:2]):
                continue
            pa, pb = celda[0], celda[1]
            if pa.get("fecha_defuncion") or pb.get("fecha_defuncion"):
                continue

            # madre/padre por genero
            gpa = (pa.get("genero") or "").lower()
            gpb = (pb.get("genero") or "").lower()
            if gpa.startswith("f"):
                madre, padre = pa, pb
            elif gpb.startswith("f"):
                madre, padre = pb, pa
            else:
                continue  # no se pudo determinar madre

            edad_madre = _edad_simulada(madre, self.hoy)
            if edad_madre is None:
                # fallback si no hay 'edad' simulada
                edad_madre = _edad_por_fecha_iso(madre.get("fecha_nacimiento",""), self.hoy)
            if edad_madre is None or not (18 <= edad_madre <= 45):
                continue

            out.append({
                "familia": familia,
                "col_idx": col_idx,
                "madre": madre,
                "padre": padre,
            })
        return out

    def _crear_bebe_dict_local(self, hoy_iso: str, padre: dict, madre: dict) -> dict:
        """Crea el bebé con banderas que tu renderer espera (nivel, tipo, mostrar_en_arbol)."""
        genero = "Femenino" if self.rng.random() < 0.5 else "Masculino"
        nombre = self.rng.choice(self.nombres_f if genero == "Femenino" else self.nombres_m)
        ap1 = (padre.get("apellidos") or "").split()[0] if padre else ""
        ap2 = (madre.get("apellidos") or "").split()[0] if madre else ""
        apellidos = f"{ap1} {ap2}".strip()
        provincia = padre.get("residencia") or madre.get("residencia") or "San José"
        persona_key = (nombre, apellidos, hoy_iso)
        cedula = db._cedula(provincia, int(hoy_iso[:4]), persona_key)
        return {
            "tipo": "persona",
            "mostrar_en_arbol": True,
            "nivel": 3,  # hijos en fila 3 según tu convención

            "nombre": nombre,
            "apellidos": apellidos,
            "nombre_completo": f"{nombre} {apellidos}",
            "cedula": cedula,
            "fecha_nacimiento": hoy_iso,
            "fecha_defuncion": "",
            "genero": genero,
            "residencia": provincia,
            "estado_civil": "Soltero",
            "afinidades": [],
            "padre_cedula": padre.get("cedula",""),
            "madre_cedula": madre.get("cedula",""),
            "edad": 0,
        }

    def _auto_nacimientos_tick(self, max_bebes_por_pareja: int = 2) -> List[Cambio]:
        """
        Crea bebés en (3, col) únicamente para parejas existentes en (2, col),
        con probabilidad self.prob_nacimiento_por_pareja_por_tick y
        máximo `max_bebes_por_pareja` por pareja en este tick.
        """
        eventos: List[Cambio] = []
        hoy_iso = self.hoy.isoformat()

        for fam in db.listar_familias():
            parejas = self._parejas_validas_en_fila2(fam)
            if not parejas:
                continue

            # Si querés solo una pareja random por familia, descomenta esta línea:
            # parejas = [self.rng.choice(parejas)]

            for pareja in parejas:
                col_idx = pareja["col_idx"]
                padre = pareja["padre"]
                madre = pareja["madre"]

                bebes_creados = 0
                intentos = 0
                max_intentos = max(1, max_bebes_por_pareja * 3)  # evita bucles si prob es baja

                while bebes_creados < max_bebes_por_pareja and intentos < max_intentos:
                    intentos += 1
                    if self.rng.random() >= self.prob_nacimiento_por_pareja_por_tick:
                        continue  # este intento no nace

                    bebe = self._crear_bebe_dict_local(hoy_iso, padre, madre)

                    # Insertar en fila 3, misma columna
                    db.agregar_persona(bebe, fam, 3, col_idx)

                    # Registrar en padres
                    padre.setdefault("hijos", []).append(bebe["cedula"])
                    madre.setdefault("hijos", []).append(bebe["cedula"])

                    # Evento para UI
                    eventos.append({
                        "tipo": "nacimiento",
                        "familia": fam,
                        "columna": col_idx,
                        "fila": 3,
                        "nombre": bebe["nombre_completo"],
                        "cedula": bebe["cedula"],
                        "fecha": hoy_iso,
                        "padres": [
                            _nombre_completo(padre),
                            _nombre_completo(madre),
                        ],
                    })
                    bebes_creados += 1

        return eventos
