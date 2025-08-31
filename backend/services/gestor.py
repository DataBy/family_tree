# backend/services/gestor.py
from __future__ import annotations

from datetime import date
import threading
import random
from typing import Callable, Optional, Dict, Any, List, Tuple

from . import db  # usa tu db.py (misma carpeta services)

Cambio = Dict[str, Any]  # {"tipo": "cumple|fallecimiento|union|nacimiento", ...}

def _add_years_safe(d: date, years: int) -> date:
    """Suma años manejando 29/Feb."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # 29-feb -> 28-feb del año destino
        return d.replace(month=2, day=28, year=d.year + years)

def _personas_en_familia(nombre_familia: str):
    m = db.obtener_matriz(nombre_familia) or []
    for fila in m:
        for celda in fila:
            for p in celda:
                yield p

def _vivas(personas):
    for p in personas:
        if not p.get("fecha_defuncion"):
            yield p

def _nombre_completo(p: dict) -> str:
    return p.get("nombre_completo") or f"{p.get('nombre','').strip()} {p.get('apellidos','').strip()}".strip()

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
    """Probabilidad simple, creciente con la edad (ajustable)."""
    if edad is None:
        return 0.001
    if edad < 1:
        return 0.001
    if edad < 40:
        return 0.002
    if edad < 60:
        return 0.005
    if edad < 75:
        return 0.015
    if edad < 85:
        return 0.04
    return 0.08

def _primer_apellido(apellidos: str) -> str:
    return (apellidos or "").split()[0] if apellidos else ""

def _apellidos_hijo(padre: dict, madre: dict) -> str:
    return f"{_primer_apellido(padre.get('apellidos',''))} {_primer_apellido(madre.get('apellidos',''))}".strip()

def _genero_opuesto(g1: str, g2: str) -> bool:
    if not g1 or not g2:
        return False
    return (g1.lower().startswith("f") and g2.lower().startswith("m")) or (g1.lower().startswith("m") and g2.lower().startswith("f"))

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

        self.nombres_m = ["Carlos", "Luis", "Mateo", "Diego", "Gabriel", "Bruno", "Iker", "Tomás", "Daniel", "Lucas", "Nicolás"]
        self.nombres_f = ["María", "Ana", "Sofía", "Valeria", "Emma", "Camila", "Lucía", "Sara", "Zoe", "Luna", "Mía"]

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

    # ---------------- Lógica del tick ----------------
    def _tick(self) -> List[Cambio]:
        eventos: List[Cambio] = []

        # Avanza el "hoy" simulado
        self.hoy = _add_years_safe(self.hoy, self.anios_por_tick)

        # 1) Cumpleaños/edad: TODAS las personas vivas incrementan +anios_por_tick
        for fam in db.listar_familias():
            for p in _vivas(_personas_en_familia(fam)):
                e = _edad_simulada(p, self.hoy)
                if e is None:
                    # si no se pudo calcular, inicializa a 0 antes de sumar
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

        # 2) Fallecimientos aleatorios (solo vivos)
        for fam in db.listar_familias():
            for p in _vivas(_personas_en_familia(fam)):
                edad = _edad_simulada(p, self.hoy)
                if self.rng.random() < _prob_muerte(edad):
                    p["fecha_defuncion"] = self.hoy.isoformat()
                    eventos.append({
                        "tipo": "fallecimiento",
                        "familia": fam,
                        "cedula": p.get("cedula",""),
                        "nombre": _nombre_completo(p),
                        "fecha": self.hoy.isoformat(),
                    })

        # 3) Uniones por familia (M/F, compatibilidad suficiente)
        for fam in db.listar_familias():
            uniones_hechas = 0
            if uniones_hechas >= self.max_uniones_por_familia_por_tick:
                continue

            vivos = [p for p in _vivas(_personas_en_familia(fam))]
            solteros_m = [p for p in vivos if (p.get("estado_civil","Soltero") != "Casado") and str(p.get("genero","")).lower().startswith("m")]
            solteros_f = [p for p in vivos if (p.get("estado_civil","Soltero") != "Casado") and str(p.get("genero","")).lower().startswith("f")]

            # Baraja para aleatoriedad
            self.rng.shuffle(solteros_m)
            self.rng.shuffle(solteros_f)

            intentos = 0
            max_intentos = 8  # evita loops largos
            while uniones_hechas < self.max_uniones_por_familia_por_tick and solteros_m and solteros_f and intentos < max_intentos:
                intentos += 1
                m = solteros_m[0]
                f = solteros_f[0]

                # Compatibilidad usando tu validador
                ok, score, reasons = db.validar_union(fam, _nombre_completo(m), _nombre_completo(f))
                if ok:
                    ok2, msg = db.unir_pareja(fam, _nombre_completo(m), _nombre_completo(f))
                    if ok2:
                        m["estado_civil"] = "Casado"
                        f["estado_civil"] = "Casado"
                        eventos.append({
                            "tipo": "union",
                            "familia": fam,
                            "pareja": [_nombre_completo(m), _nombre_completo(f)],
                            "compatibilidad": int(round(score)),
                            "mensaje": msg,
                        })
                        uniones_hechas += 1
                        solteros_m.pop(0)
                        solteros_f.pop(0)
                    else:
                        # no se pudo ubicar la celda, descarta este pareo
                        solteros_m.pop(0)
                        solteros_f.pop(0)
                else:
                    # intenta con otras combinaciones simples
                    self.rng.shuffle(solteros_m)
                    self.rng.shuffle(solteros_f)

        # 4) Nacimientos (por parejas en fila 2)
        for fam in db.listar_familias():
            matriz = db.obtener_matriz(fam) or []
            if len(matriz) <= 2:
                continue  # no hay fila de parejas
            fila_parejas = matriz[2]
            for col_idx, celda in enumerate(fila_parejas):
                if len(celda) < 2:
                    continue
                pa, pb = celda[0], celda[1]
                # Ambos vivos
                if pa.get("fecha_defuncion") or pb.get("fecha_defuncion"):
                    continue
                # Identificar madre/padre por genero
                if str(pa.get("genero","")).lower().startswith("f"):
                    madre, padre = pa, pb
                else:
                    madre, padre = pb, pa
                # Rango fértil de la madre 18-45 (por edad simulada)
                edad_madre = _edad_simulada(madre, self.hoy)
                if edad_madre is None or not (18 <= edad_madre <= 45):
                    continue
                # Probabilidad de nacimiento por tick
                if self.rng.random() >= self.prob_nacimiento_por_pareja_por_tick:
                    continue

                # Generar bebé
                genero_bebe = "Femenino" if self.rng.random() < 0.5 else "Masculino"
                nombre_bebe = self.rng.choice(self.nombres_f if genero_bebe.startswith("F") else self.nombres_m)
                apellidos_bebe = _apellidos_hijo(padre, madre)

                # Inserta en fila 3 (una debajo de parejas) y misma columna
                fila_hijos = 3
                p_bebe = db._p_col(
                    col_idx,
                    nombre_bebe,
                    apellidos_bebe,
                    genero_bebe,
                    tag=f"SIM-{self.hoy.year}",
                    fecha_nac=self.hoy.isoformat(),
                    residencia=None,
                    estado_civil="Soltero",
                    fecha_def=""
                )
                # Enlaza padres
                p_bebe["padre_cedula"] = padre.get("cedula","")
                p_bebe["madre_cedula"] = madre.get("cedula","")
                # Inicializa edad explícita en 0 (simulación)
                p_bebe["edad"] = 0

                db.agregar_persona(p_bebe, fam, fila_hijos, col_idx)
                # Guarda relación de hijos en los padres (opcional)
                padre.setdefault("hijos", []).append(p_bebe["cedula"])
                madre.setdefault("hijos", []).append(p_bebe["cedula"])

                eventos.append({
                    "tipo": "nacimiento",
                    "familia": fam,
                    "columna": col_idx,
                    "fila": fila_hijos,
                    "nombre": f"{p_bebe['nombre']} {p_bebe['apellidos']}",
                    "cedula": p_bebe["cedula"],
                    "fecha": self.hoy.isoformat(),
                    "padres": [_nombre_completo(padre), _nombre_completo(madre)],
                })

        # Notificar UI
        if self.on_change:
            try:
                self.on_change(eventos)
            except Exception:
                # El callback nunca debe romper el bucle de simulación
                pass

        return eventos
