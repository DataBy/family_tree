# backend/services/nacimientos.py
from __future__ import annotations
from datetime import date, datetime  # Añadido datetime al import
from typing import Dict, List, Optional
from . import db
import random
import logging

logger = logging.getLogger(__name__)

class GestorNacimientos:
    """Maneja eventos de nacimientos en la simulación"""
    
    def __init__(self):
        # Contadores para generar cédulas únicas
        self._contador_por_prov: Dict[str, int] = {}
        # Prefijo de cédula por provincia
        self.PROV_PREFIJO = {
            "San José": "1",
            "Alajuela": "2", 
            "Cartago": "3",
            "Heredia": "4",
            "Guanacaste": "5",
            "Puntarenas": "6",
            "Limón": "7",
        }
    
    def _generar_cedula(self, provincia: str, anio: int) -> str:
        """Genera una cédula única: <prefijo_prov><YYYY><####>"""
        pref = self.PROV_PREFIJO.get(provincia, "1")
        self._contador_por_prov[provincia] = self._contador_por_prov.get(provincia, 0) + 1
        sec = self._contador_por_prov[provincia]
        return f"{pref}{anio:04d}{sec:04d}"
    
    def _generar_nombre_bebe(self, genero: str) -> str:
        """Genera un nombre aleatorio para un bebé"""
        nombres_hombres = [
            "Carlos", "José", "Luis", "Antonio", "Miguel", "Juan", "Pedro", "David",
            "Andrés", "Alejandro", "Manuel", "Francisco", "Jorge", "Ricardo", "Mario",
            "Santiago", "Sebastián", "Mateo", "Diego", "Daniel"
        ]
        nombres_mujeres = [
            "María", "Ana", "Carmen", "Laura", "Sofía", "Elena", "Isabel", "Patricia",
            "Valeria", "Gabriela", "Fernanda", "Daniela", "Andrea", "Paula", "Claudia",
            "Camila", "Valentina", "Lucía", "Martina", "Julieta"
        ]
        
        if genero.lower() == "masculino":
            return random.choice(nombres_hombres)
        else:
            return random.choice(nombres_mujeres)
    
    def _generar_apellidos_bebe(self, padre: Dict, madre: Dict) -> str:
        """Genera apellidos para un bebé combinando los de los padres"""
        # Combina primer apellido del padre con primer apellido de la madre
        apellido_padre = padre.get("apellidos", "").split()[0] if padre.get("apellidos") else "Padre"
        apellido_madre = madre.get("apellidos", "").split()[0] if madre.get("apellidos") else "Madre"
        return f"{apellido_padre} {apellido_madre}"
    
    def procesar_nacimientos(self, nombre_familia: str) -> Dict[str, any]:
        """
        Procesa nacimientos en una familia según las reglas:
        - Parejas compatibles pueden tener hijos
        - Solo parejas casadas/unidas
        """
        if not db.existe_familia(nombre_familia):
            return {"error": f"Familia {nombre_familia} no existe"}
        
        matriz = db.obtener_matriz(nombre_familia)
        if not matriz:
            return {"error": "Matriz de familia vacía"}
        
        nuevos_nacimientos = []
        errores = []
        
        try:
            # Buscar parejas en filas 0 y 2 (filas de parejas)
            for fila_parejas in [0, 2]:
                if fila_parejas < len(matriz):
                    for col, celda in enumerate(matriz[fila_parejas]):
                        # Verificar si hay pareja (2 personas en la celda)
                        if len(celda) >= 2:
                            pareja1 = celda[0]
                            pareja2 = celda[1]
                            
                            # Verificar condiciones para tener hijos
                            if self._puede_tener_hijos(pareja1, pareja2):
                                # Probabilidad de nacimiento (30%)
                                if random.random() < 0.3:
                                    try:
                                        nuevo_bebe = self._crear_nacimiento(
                                            pareja1, pareja2, nombre_familia, fila_parejas + 1, col
                                        )
                                        nuevos_nacimientos.append(nuevo_bebe)
                                    except Exception as e:
                                        errores.append(f"Error creando bebé: {str(e)}")
            
            # Agregar nuevos nacimientos a la base de datos
            for bebe in nuevos_nacimientos:
                try:
                    db.agregar_persona(
                        bebe, 
                        nombre_familia, 
                        bebe.get("_fila_destino", 3), 
                        bebe.get("_col_destino", 0)
                    )
                except Exception as e:
                    errores.append(f"Error agregando bebé a DB: {str(e)}")
            
            return {
                "familia": nombre_familia,
                "nacimientos": len(nuevos_nacimientos),
                "detalles": nuevos_nacimientos,
                "errores": errores
            }
            
        except Exception as e:
            return {"error": f"Error procesando nacimientos: {str(e)}"}
    
    def _puede_tener_hijos(self, persona1: Dict, persona2: Dict) -> bool:
        """Verifica si una pareja puede tener hijos según las reglas"""
        try:
            # Ambas deben estar vivas
            if (persona1.get("fecha_defuncion") or persona2.get("fecha_defuncion")):
                return False
            
            # Ambas deben estar casadas/unidas
            estado1 = (persona1.get("estado_civil") or "").lower()
            estado2 = (persona2.get("estado_civil") or "").lower()
            if estado1 not in ["casado", "casada"] or estado2 not in ["casado", "casada"]:
                return False
            
            # Calcular edades
            fecha_nac1 = self._parse_fecha(persona1.get("fecha_nacimiento", ""))
            fecha_nac2 = self._parse_fecha(persona2.get("fecha_nacimiento", ""))
            
            if not fecha_nac1 or not fecha_nac2:
                return False
            
            hoy = date.today()
            edad1 = hoy.year - fecha_nac1.year - ((hoy.month, hoy.day) < (fecha_nac1.month, fecha_nac1.day))
            edad2 = hoy.year - fecha_nac2.year - ((hoy.month, hoy.day) < (fecha_nac2.month, fecha_nac2.day))
            
            # Ambos deben ser mayores de 18 años
            if edad1 < 18 or edad2 < 18:
                return False
            
            # Diferencia de edad ≤ 15 años
            if abs(edad1 - edad2) > 15:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando posibilidad de hijos: {e}")
            return False
    
    def _parse_fecha(self, fecha_str: str) -> Optional[date]:
        """Parsea una fecha desde string"""
        if not fecha_str:
            return None
        try:
            return datetime.strptime(fecha_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None
    
    def _crear_nacimiento(self, padre: Dict, madre: Dict, familia: str, fila_destino: int, col_destino: int) -> Dict:
        """Crea un nuevo nacimiento"""
        hoy = date.today()
        
        # Determinar género aleatoriamente
        genero = "Masculino" if random.choice([True, False]) else "Femenino"
        
        # Generar nombre
        nombre = self._generar_nombre_bebe(genero)
        
        # Generar apellidos
        apellidos = self._generar_apellidos_bebe(padre, madre)
        
        # Generar cédula
        provincia = padre.get("residencia", "San José")
        cedula = self._generar_cedula(provincia, hoy.year)
        
        nuevo_bebe = {
            "nombre": nombre,
            "apellidos": apellidos,
            "nombre_completo": f"{nombre} {apellidos}",
            "cedula": cedula,
            "fecha_nacimiento": hoy.strftime("%Y-%m-%d"),
            "fecha_defuncion": "",
            "genero": genero,
            "residencia": provincia,
            "estado_civil": "Soltero",
            "_fila_destino": fila_destino,
            "_col_destino": col_destino
        }
        
        logger.info(f"Nuevo nacimiento: {nombre} {apellidos} en familia {familia}")
        return nuevo_bebe

# Instancia global para uso en la aplicación
gestor_nacimientos = GestorNacimientos()