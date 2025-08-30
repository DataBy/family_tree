from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, request
import json
import unicodedata
import os
import re
from services import db, buscador

app = Flask(__name__)
app.secret_key = "supersecreto"  # Necesario para flash

# Limpiar Cookies
import uuid
BOOT_ID = uuid.uuid4().hex

# ---- Contexto común para las vistas que muestran el selector de familia
def ctx():
    return {
        "familias": db.listar_familias(),
        "familia_activa": session.get("familia_activa"),
    }

@app.route("/")
def iniciador():
    return render_template("iniciador.html", **ctx())

@app.route("/home")
def home():
    return render_template("home.html", **ctx())

@app.route("/personas", methods=["GET", "POST"])
def personas():
    if request.method == "POST":
        familia = session.get("familia_activa")
        if not familia or not db.existe_familia(familia):
            flash("⚠️ Seleccioná una familia antes de agregar personas")
            return redirect(url_for("personas"))

        persona = {
            "nombre": request.form.get("nombre"),
            "apellidos": request.form.get("apellidos"),
            "cedula": request.form.get("cedula"),
            "fecha_nacimiento": request.form.get("fecha_nacimiento"),
            "fecha_defuncion": request.form.get("fecha_defuncion"),
            "genero": request.form.get("genero"),
            "residencia": request.form.get("residencia"),
            "estado_civil": request.form.get("estado_civil"),
        }

        try:
            nivel = int((request.form.get("nivel") or "").strip())
            subfamilia = int((request.form.get("subfamilia") or "").strip())
        except ValueError:
            flash("⚠️ Nivel y subfamilia deben ser números.")
            return redirect(url_for("personas"))

        try:
            db.agregar_persona(persona, familia, nivel, subfamilia)
            flash(f"✅ Persona agregada a la familia “{familia}”.")
        except ValueError as e:
            flash(str(e))

        return redirect(url_for("personas"))

    return render_template("personas.html", **ctx())

@app.route("/ver_matriz")
def ver_matriz():
    fam = session.get("familia_activa")
    matriz = db.obtener_matriz(fam) if fam else None
    return {
        "familia_activa": fam,
        "matriz": matriz,
        "todas_familias": db.listar_familias(),
    }

@app.route("/tree")
def tree():
    fam = session.get("familia_activa")
    matriz = db.obtener_matriz(fam) if fam else None

    def to_elements(matriz):
        if not matriz:
            return []

        # ====== Layout espacioso ======
        CELL_W = 560
        CELL_H = 300
        PAD_X  = 180
        PAD_Y  = 140
        SLOT   = 180  # separación dentro de la celda (parejas)

        def base_pos(r, c):
            return (PAD_X + c * CELL_W, PAD_Y + r * CELL_H)

        # --- clave única por persona ---
        def person_key(p: dict) -> str:
            ced = (p.get("cedula") or "").strip()
            if ced:
                return f"ced-{ced}"
            # fallback razonable si no hay cédula
            nom = (p.get("nombre") or "").strip()
            ape = (p.get("apellidos") or "").strip()
            nac = (p.get("fecha_nacimiento") or "").strip()
            return f"nf-{nom}|{ape}|{nac}"

        def photo_url(p: dict) -> str:
            genero = (p.get("genero") or "").lower()
            digits = "".join(ch for ch in (p.get("cedula") or "") if ch.isdigit())
            seed = int(digits[-2:], 10) % 90 if digits else 0
            if "fem" in genero:
                return f"https://randomuser.me/api/portraits/women/{seed}.jpg"
            if "mas" in genero:
                return f"https://randomuser.me/api/portraits/men/{seed}.jpg"
            return f"https://picsum.photos/seed/{seed}/200/200"

        def is_couple_row(r: int) -> bool:
            # En tu convención, parejas en filas 0 y 2
            return r in (0, 2)

        elements = []

        # Mapas para deduplicar:
        #   key_persona -> node_id (único en el grafo)
        #   pos_id(r-c-i) -> node_id (para “resolver” al crear edges)
        seen_person: dict[str, str] = {}
        pos_to_node: dict[str, str]  = {}

        # --- 1) Crear nodos de personas (SIN duplicar) ---
        for r, fila in enumerate(matriz or []):
            for c, celda in enumerate(fila):
                n = len(celda)
                for i, p in enumerate(celda):
                    pos_id = f"{r}-{c}-{i}"
                    k = person_key(p)

                    if k in seen_person:
                        # Ya existe: no dibujamos otro nodo, solo mapeamos posición->nodo existente
                        pos_to_node[pos_id] = seen_person[k]
                        continue

                    # Crear nodo NUEVO
                    node_id = f"p-{k}"
                    seen_person[k] = node_id
                    pos_to_node[pos_id] = node_id

                    x0, y0 = base_pos(r, c)
                    offset = (i - (n - 1) / 2) * SLOT
                    fallecido = bool((p.get("fecha_defuncion") or "").strip())
                    detalle = (
                        f"<b>{p.get('nombre','')} {p.get('apellidos','')}</b><br>"
                        f"Cédula: {p.get('cedula','—')}<br>"
                        f"Nac: {p.get('fecha_nacimiento','—')}"
                        + (f"<br>Fallec: {p['fecha_defuncion']}" if fallecido else "")
                    )

                    elements.append({
                        "data": {
                            "id": node_id,
                            "kind": "person",
                            "label": f"{p.get('nombre','')} {p.get('apellidos','')}",
                            "detalle": detalle,
                            "img": photo_url(p),
                            "fallecido": 1 if fallecido else 0
                        },
                        "position": {"x": x0 + offset, "y": y0}
                    })

        # --- 2) Uniones matrimoniales centradas + edges ---
        for r, fila in enumerate(matriz or []):
            if not is_couple_row(r):
                continue

            for c, celda in enumerate(fila):
                # parejas por pares consecutivos [0,1], [2,3], ...
                pairs = [(k, k + 1) for k in range(0, len(celda) - 1, 2)]
                for pair_idx, (iA, iB) in enumerate(pairs):
                    # Resolver cada posición a su node_id real (deduplicado)
                    idA = pos_to_node.get(f"{r}-{c}-{iA}")
                    idB = pos_to_node.get(f"{r}-{c}-{iB}")
                    if not idA or not idB:
                        continue

                    # Nodo "unión" centrado (punto del que cuelgan hijos)
                    x0, y0 = base_pos(r, c)
                    union_id = f"u-{r}-{c}-{pair_idx}"
                    elements.append({
                        "data": {"id": union_id, "kind": "union"},
                        "position": {"x": x0, "y": y0 + 12}
                    })

                    # Matrimonio: dos segmentos hacia el centro (unión)
                    elements.append({
                        "data": {"id": f"mA-{r}-{c}-{pair_idx}",
                                 "source": idA, "target": union_id, "etype": "marriage"}
                    })
                    elements.append({
                        "data": {"id": f"mB-{r}-{c}-{pair_idx}",
                                 "source": idB, "target": union_id, "etype": "marriage"}
                    })

                    # Hijos: fila r+1, misma columna c (cuelgan de la unión)
                    if r + 1 < len(matriz) and c < len(matriz[r + 1]):
                        for j in range(len(matriz[r + 1][c])):
                            child_node = pos_to_node.get(f"{r+1}-{c}-{j}")
                            if not child_node:
                                continue
                            elements.append({
                                "data": {"id": f"h-{union_id}-{child_node}",
                                         "source": union_id, "target": child_node, "etype": "child"}
                            })

        return elements

    elements = to_elements(matriz)
    return render_template("tree.html", elements=elements, **ctx())

# ---- Familias: crear y seleccionar
@app.route("/familia/nueva", methods=["POST"])
def crear_familia():
    nombre = (request.form.get("nombre_familia") or "").strip()
    if db.crear_familia(nombre):
        session["familia_activa"] = nombre
        flash(f"✅ Familia “{nombre}” creada y seleccionada.")
    else:
        flash("⚠️ Nombre vacío o la familia ya existe.")
    return redirect(request.referrer or url_for("personas"))

@app.route("/familia/seleccionar", methods=["POST"])
def seleccionar_familia():
    nombre = (request.form.get("nombre_familia") or "").strip()
    if db.existe_familia(nombre):
        session["familia_activa"] = nombre
        flash(f"✅ Familia “{nombre}” activada.")
    else:
        flash("⚠️ La familia no existe.")
    return redirect(request.referrer or url_for("personas"))



# Limpiar reinicio del servidor
@app.before_request
def _reset_si_reinicio():
    if session.get("boot_id") != BOOT_ID:
        session.clear()
        session["boot_id"] = BOOT_ID




# Lógica de search:

@app.route("/search")
def search():
    return render_template("search.html", **ctx())   # dejamos SOLO esta versión


# Cargar JSON de respuestas
BASE_DIR = os.path.dirname(__file__)  # carpeta backend
DATA_PATH = os.path.join(BASE_DIR, "data", "responses.json")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    RESPONSES = json.load(f)


def normalize_text(text: str) -> str:
    """Convierte texto a minúsculas, elimina tildes y signos raros."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    # quitar signos de puntuación y caracteres no alfanuméricos (excepto espacios)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return text.strip()



def get_active_family_and_matrix():
    fam = session.get("familia_activa")
    if not fam or not db.existe_familia(fam):
        fam = next(iter(db.familias), None)  # primera familia disponible
    matriz = db.obtener_matriz(fam) if fam else []
    return fam, (matriz or [])

@app.route("/chat", methods=["POST"])
def chat():
    user_raw = (request.form.get("query") or "").strip()
    user_msg = normalize_text(user_raw)

    # Exponer matriz al módulo 'buscador'
    fam, matriz = get_active_family_and_matrix()
    setattr(buscador, "matriz", matriz)  # <- clave para que 'relacion()' funcione

    reply = None

    # ----- saludos/despedidas -----
    if any(saludo in user_msg for saludo in ["hola", "buenas", "hey"]):
        reply = RESPONSES["saludos"][0]

    elif any(desp in user_msg for desp in ["adios", "chao", "bye"]):
        reply = RESPONSES["despedidas"][0]

    # ----- P1: relación A-B -----
    elif "relacion" in user_msg and "entre" in user_msg:
        try:
            after_entre = user_msg.split("entre", 1)[1].strip()
            partes = after_entre.split(" y ")
            if len(partes) == 2:
                persona_a = partes[0].replace("persona", "").strip()
                persona_b = partes[1].replace("persona", "").strip()
                reply = buscador.relacion(persona_a, persona_b)
            else:
                reply = "No entendí los nombres de las personas."
        except Exception as e:
            reply = f"Error al procesar los nombres: {e}"

     # -----------------------
    # P2: Primos de X (sin helpers; basado en normalize_text)
    elif "primos" in user_msg:
        # Quitamos ruidos comunes para que el nombre quede limpio
        texto = user_msg
        texto = texto.replace("de primer grado", "").replace("primer grado", "")
        # Extrae lo que venga después de "primos" o "primos de"
        m = re.search(r"primos(?:\s+de)?\s+(?P<nombre>.+)$", texto)
        if m:
            nombre = m.group("nombre").strip().strip("?!.:,;").strip()
        else:
            nombre = user_msg.split()[-1].strip("?!.:,;")
        lista = buscador.primos_primer_grado(nombre)
        reply = f"Primos de primer grado de {nombre.title()}: {', '.join(lista) if lista else 'ninguno'}."

    # -----------------------
    # P3: Antepasados maternos de X (sin helpers)
    elif "antepasados" in user_msg and "maternos" in user_msg:
        m = re.search(r"\bantepasados\s+maternos(?:\s+de)?\s+(?P<nombre>.+)$", user_msg)
        raw = m.group("nombre") if m else (user_msg.split()[-1] if user_msg.split() else "")
        stop = {"de", "la", "el", "los", "las", "y", "del", "al", "persona", "personas"}
        nombre_tokens = [t for t in raw.split() if t not in stop and not t.isdigit()]
        nombre = " ".join(nombre_tokens).strip().title()
        cadena = buscador.antepasados_maternos(nombre) if nombre else []
        reply = f"Antepasados maternos de {nombre or '—'}: {', '.join(cadena) if cadena else 'ninguno'}."

    # -----------------------
    elif "descendientes" in user_msg and "vivos" in user_msg:
    # Soporta: "descendientes de X vivos", "cuales descendientes de X estan vivos actualmente", etc.
    # (trabajamos sobre user_msg ya normalizado)
        m = re.search(
            r"descendientes(?:\s+de)?\s+(?P<nombre>.+?)\s+(?:estan\s+)?vivos\b",
            user_msg
        )
        if m:
            nombre = m.group("nombre").strip()
        else:
            # Fallback: toma lo que sigue a "descendientes de" y limpia ruido al final
            m2 = re.search(r"descendientes(?:\s+de)?\s+(?P<nombre>.+)$", user_msg)
            nombre = (m2.group("nombre") if m2 else user_msg).strip()

        # Quitar tokens de cierre *iterativamente* (no solo uno)
        ruido_final = {"estan", "esta", "vivos", "actualmente", "ahora", "hoy"}
        toks = [t for t in nombre.split() if t]
        while toks and toks[-1] in ruido_final:
            toks.pop()
        nombre = " ".join(toks)

        lista = buscador.descendientes_vivos(nombre)
        reply = f"Descendientes vivos de {nombre.title()}: {', '.join(lista) if lista else 'ninguno'}."

    # ----- P5: nacidos últimos 10 años -----
    elif "ultimos 10 anos" in user_msg or "ultimos 10 años" in user_msg:
        actuales = db.nacidos_ultimos_10_anios(fam) if fam else []
        reply = f"Nacidos en los últimos 10 años: {', '.join(actuales) or 'ninguno'}."

    # ----- P6: parejas con 2+ hijos -----
    elif "parejas" in user_msg and "hijos" in user_msg:
        lista = buscador.parejas_con_mas_de_dos_hijos()
        reply = f"Parejas con 2 o más hijos: {', '.join(lista) if lista else 'ninguna'}."

    # ----- P7: fallecidos <50 -----
    elif "fallecieron" in user_msg and "50" in user_msg:
        menores = db.fallecidos_menores_de_50(fam) if fam else []
        reply = f"Personas fallecidas antes de los 50: {', '.join(menores) or 'ninguna'}."

    # ----- default -----
    if not reply:
        reply = RESPONSES["default"]

    return jsonify({"reply": reply})






# =========================
# Historial / Línea de tiempo
# =========================
def _norm_name(s: str) -> str:
    s = (s or '').strip().lower()
    s = unicodedata.normalize('NFD', s)
    return ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')

def _full_name(p: dict) -> str:
    return (p.get('nombre_completo')
            or f"{p.get('nombre','')} {p.get('apellidos','')}".strip())

def _year_from_date(s: str | None) -> int | None:
    s = (s or '').strip()
    return int(s[:4]) if len(s) >= 4 and s[:4].isdigit() else None

@app.route("/history")
def history():
    # Renderiza tu template de historial con el contexto de familia
    return render_template("history.html", **ctx())

@app.route("/api/history")
def api_history():
    """
    Devuelve JSON con:
      {
        "persona": { nombre_completo, genero, estado_civil, ... },
        "eventos": [ {tipo, anio, detalle}, ... ]  // ordenado por año
      }
    Tipos: nacimiento, union_pareja, tuvo_hijo, enviudo, fallecimiento
    """
    nombre_q = (request.args.get("nombre") or "").strip()
    if not nombre_q:
        return jsonify({"persona": None, "eventos": []})

    # Familia/matriz activa (usa la de sesión o la primera disponible)
    fam = session.get("familia_activa")
    if not fam or fam not in db.familias:
        fam = next(iter(db.familias), None)
    matriz = db.familias.get(fam, [])

    # Buscar persona y sus posiciones
    target = None
    positions: list[tuple[int,int,int]] = []
    tnorm = _norm_name(nombre_q)

    for r, fila in enumerate(matriz):
        for c, celda in enumerate(fila):
            for i, p in enumerate(celda):
                if _norm_name(_full_name(p)) == tnorm:
                    if target is None:
                        target = p
                    positions.append((r, c, i))

    if not target:
        # No encontrada
        return jsonify({"persona": None, "eventos": []})

    # Recolectar cónyuges y descendencia directa por columna
    spouses: list[dict] = []
    children: list[dict] = []
    seen_spouse = set()
    seen_child = set()

    for (r, c, i) in positions:
        # Filas de pareja en tu modelo: 0 y 2 (fila siguiente contiene hijos)
        if r in (0, 2):
            # Encontrar cónyuge en la misma celda por pares [0,1], [2,3], ...
            base = (i // 2) * 2
            pair_idx = [base, base + 1]
            for j in pair_idx:
                if j == i:
                    continue
                if 0 <= j < len(matriz[r][c]):
                    sp = matriz[r][c][j]
                    ksp = _norm_name(_full_name(sp))
                    if ksp not in seen_spouse:
                        spouses.append(sp)
                        seen_spouse.add(ksp)

            # Hijos: fila r+1, misma columna c
            if r + 1 < len(matriz) and c < len(matriz[r + 1]):
                for ch in matriz[r + 1][c]:
                    kch = _norm_name(_full_name(ch))
                    if kch not in seen_child:
                        children.append(ch)
                        seen_child.add(kch)

    # Construcción de eventos
    eventos: list[dict] = []

    # Nacimiento
    y_nac = _year_from_date(target.get("fecha_nacimiento"))
    if y_nac:
        eventos.append({"tipo": "nacimiento", "anio": y_nac, "detalle": ""})

    # Hijos (un evento por cada hijo)
    for ch in children:
        yh = _year_from_date(ch.get("fecha_nacimiento"))
        eventos.append({
            "tipo": "tuvo_hijo",
            "anio": yh,
            "detalle": _full_name(ch)
        })

    # Unión de pareja (1 evento por cónyuge; año estimado como el del primer hijo - 1 si se puede)
    # Si no hay hijos, se deja sin año.
    earliest_child_years = [ _year_from_date(ch.get("fecha_nacimiento")) for ch in children if _year_from_date(ch.get("fecha_nacimiento")) ]
    est_union_year = (min(earliest_child_years) - 1) if earliest_child_years else None

    for sp in spouses:
        eventos.append({
            "tipo": "union_pareja",
            "anio": est_union_year,
            "detalle": _full_name(sp)
        })

    # Enviudó (si alguno de los cónyuges tiene fecha_defuncion)
    for sp in spouses:
        y_def_sp = _year_from_date(sp.get("fecha_defuncion"))
        if y_def_sp:
            eventos.append({
                "tipo": "enviudo",
                "anio": y_def_sp,
                "detalle": f"Por muerte de {_full_name(sp)}"
            })

    # Fallecimiento
    y_def = _year_from_date(target.get("fecha_defuncion"))
    if y_def:
        eventos.append({"tipo": "fallecimiento", "anio": y_def, "detalle": ""})

    # Orden cronológico (los eventos sin año van al final)
    def sort_key(ev: dict):
        a = ev.get("anio")
        return (a is None, a, ev.get("tipo", ""))

    eventos.sort(key=sort_key)

    persona_payload = {
        "nombre_completo": _full_name(target),
        "genero": target.get("genero"),
        "estado_civil": target.get("estado_civil"),
        "cedula": target.get("cedula"),
        "residencia": target.get("residencia"),
        "fecha_nacimiento": target.get("fecha_nacimiento"),
        "fecha_defuncion": target.get("fecha_defuncion"),
    }

    return jsonify({"persona": persona_payload, "eventos": eventos})



# ------------------ MAIN ------------------
if __name__ == "__main__":
    app.run(debug=True)
