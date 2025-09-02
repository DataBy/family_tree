# 🌳 Family Tree - Sistema de Árbol Genealógico

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)  
![Flask](https://img.shields.io/badge/Flask-Backend-black?logo=flask)  
![Tailwind](https://img.shields.io/badge/Tailwind-CSS-38B2AC?logo=tailwind-css)  
![Cytoscape](https://img.shields.io/badge/Cytoscape.js-Graph-green)  

Este es un sistema educativo y visual, desarrollado como proyecto de programación, que permite registrar familias, gestionar sus integrantes y visualizar un árbol genealógico interactivo. El sistema también simula eventos familiares como nacimientos, cumpleaños, uniones y fallecimientos. Fue desarrollado en **Python** usando **Flask** para el backend y **Cytoscape.js** para la visualización del árbol.

## 🧠 Resumen

El sistema representa una simulación familiar que combina registro genealógico, gestión de relaciones y dinámica de eventos. Cada persona cuenta con información básica (cédula, nombre, fechas de nacimiento y defunción, género, residencia, estado civil).  
A lo largo del tiempo, que avanza automáticamente (1 año virtual cada 10 segundos), ocurren eventos como:

- 🎂 Cumpleaños  
- ⚰ Fallecimientos aleatorios según la edad  
- 💍 Uniones de pareja (con compatibilidad emocional y genética)  
- 👶 Nacimientos en parejas fértiles  
- 👩‍⚖️ Tutoría automática para menores huérfanos  
- 😢 Viudez y soltería prolongada con impacto en la salud emocional  

La misión principal es **gestionar y comprender las dinámicas familiares a través de generaciones** y visualizar todo en un grafo interactivo.

---

## 📁 Estructura del Proyecto

```
📦FamilyTree/
┣ 📁templates/              # Archivos HTML para la interfaz web
┃ ┣ iniciador.html          # Pantalla de inicio
┃ ┣ home.html               # Menú y selector de familias
┃ ┣ personas.html           # Formulario de registro de personas
┃ ┣ love.html               # Gestión de uniones de pareja
┃ ┣ tree.html               # Visualización del árbol genealógico
┃ ┣ search.html             # Buscador tipo chatbot
┃ ┗ history.html            # Historial y línea del tiempo
┣ 📁backend/
┃ ┣ db.py                   # Gestión de datos y familias
┃ ┣ gestor.py               # Simulador de tiempo y eventos
┃ ┣ efecto.py               # Efectos colaterales (tutores, viudez, soltería)
┃ ┗ buscador.py             # Consultas de parentesco y descendencia
┣ 📜app.py                  # Servidor principal con Flask
┣ 📜requirements.txt        # Dependencias del proyecto
┗ 📜README.md               # Este archivo
```

---

## 🛠️ Dependencias

Este proyecto fue desarrollado con:

- **Python 3.10+**  
- **Flask**  
- **Tailwind CSS**  
- **Cytoscape.js**

---

## 🚀 Cómo ejecutar

1. Cloná el repositorio:  
   ```bash
   git clone https://github.com/tu_usuario/family-tree.git
   cd family-tree
   ```

2. Instalá las dependencias con `requirements.txt`:  
   ```bash
   pip install -r requirements.txt
   ```

3. Ejecutá la aplicación:  
   ```bash
   python app.py
   ```

4. Abrí tu navegador en 👉 [http://localhost:5000](http://localhost:5000)

---

## 🔍 Consultas del chatbot disponibles

- ¿Cuál es la relación entre Persona A y Persona B?  
- ¿Quiénes son los primos de primer grado de X?  
- ¿Cuáles son los antepasados maternos de X?  
- ¿Qué descendientes vivos tiene X?  
- ¿Quiénes nacieron en los últimos 10 años?  
- ¿Qué parejas tienen 2 o más hijos en común?  
- ¿Quiénes fallecieron antes de cumplir 50 años?  

---

## 👥 Desarrolladores

- **Byron Bolaños Zamora** - [bolanoscontacto@gmail.com](mailto:bolanoscontacto@gmail.com)  
- **Javier Mendoza González** - [ag7000107@gmail.com](mailto:ag7000107@gmail.com)  

**Profesor:** Alejandro Alfaro Quesada – Curso Introducción a la Programación  

---
