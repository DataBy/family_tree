from flask import Flask, render_template, request, redirect, url_for, flash
from services import db

app = Flask(__name__)
app.secret_key = "supersecreto"  # Necesario para flash (puede ser cualquier string)

@app.route("/")
def iniciador():
    return render_template("iniciador.html")

@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/personas", methods=["GET", "POST"])
def personas():
    if request.method == "POST":
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

        nivel = int(request.form.get("nivel"))
        subfamilia = int(request.form.get("subfamilia"))

        db.agregar_persona(persona, nivel, subfamilia)

        flash("✅ Persona agregada correctamente")  # <- mensaje
        return redirect(url_for("personas"))

    return render_template("personas.html")


@app.route("/config")
def config():
    return render_template("config.html")

if __name__ == "__main__":
    app.run(debug=True)