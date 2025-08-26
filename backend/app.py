from flask import Flask, render_template, request, redirect, url_for, flash, session
from services import db

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


@app.route("/search")
def search():
    return render_template("search.html", **ctx())

if __name__ == "__main__":
    app.run(debug=True)
