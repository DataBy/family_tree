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
        elements = []
        if not matriz:
            return elements

        def get_id(r, c, i):
            return f"{r}-{c}-{i}"

        for r, fila in enumerate(matriz):
            for c, col in enumerate(fila):
                for i, persona in enumerate(col):
                    pid = get_id(r, c, i)
                    fallecido = bool(persona.get("fecha_defuncion"))
                    elements.append({
                        "data": {
                            "id": pid,
                            "label": f"{persona['nombre']} {persona['apellidos']}",
                            "detalle": f"Cédula: {persona['cedula']}<br>"
                                       f"Nac: {persona['fecha_nacimiento']}"
                                       + (f"<br>Fallec: {persona['fecha_defuncion']}" if fallecido else ""),
                            "fallecido": fallecido,
                        }
                    })
                    # conectar con la misma columna en la fila anterior
                    if r > 0 and c < len(matriz[r-1]):
                        for j, padre in enumerate(matriz[r-1][c]):
                            elements.append({
                                "data": {
                                    "id": f"e-{r}-{c}-{i}-{j}",
                                    "source": get_id(r-1, c, j),
                                    "target": pid
                                }
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

if __name__ == "__main__":
    app.run(debug=True)
