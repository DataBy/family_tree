# backend/services/fallecimientos.py
from __future__ import annotations
from datetime import date, datetime
from typing import Dict, List, Optional
from . import db
import random
import logging

logger = logging.getLogger(__name__)

class GestorFallecimientos:
    """Maneja eventos de fallecimientos en la simulación"""
    
    def procesar_fallecimientos(self, nombre_familia: str) -> Dict[str, any]:
        """
        Procesa fallecimientos aleatorios según las reglas:
        - Cada 10 segundos puede morir alguien aleatoriamente
        - Probabilidad base del 5%
        """
        if not db.existe_familia(nombre_familia):
            return {"error": f"Familia {nombre_familia} no existe"}
        
        matriz = db.obtener_matriz(nombre_familia)
        if not matriz:
            return {"error": "Matriz de familia vacía"}
        
        fallecidos = []
        errores = []
        
        try:
            # Recorrer toda la matriz buscando personas vivas
            for fila_idx, fila in enumerate(matriz):
                for col_idx, celda in enumerate(fila):
                    for persona_idx, persona in enumerate(celda):
                        # Verificar si la persona está viva
                        if not persona.get("fecha_defuncion"):
                            # Probabilidad de fallecimiento (5%)
                            if random.random() < 0.05:
                                try:
                                    fallecido = self._registrar_fallecimiento(
                                        persona, fila_idx, col_idx, persona_idx
                                    )
                                    fallecidos.append(fallecido)
                                    
                                    # Actualizar estado civil de la pareja si existe
                                    self._actualizar_pareja_viuda(
                                        persona, matriz, fila_idx, col_idx
                                    )
                                    
                                except Exception as e:
                                    errores.append(f"Error registrando fallecimiento: {str(e)}")
            
            return {
                "familia": nombre_familia,
                "fallecidos": len(fallecidos),
                "detalles": fallecidos,
                "errores": errores
            }
            
        except Exception as e:
            return {"error": f"Error procesando fallecimientos: {str(e)}"}
    
    def _registrar_fallecimiento(self, persona: Dict, fila: int, col: int, idx: int) -> Dict:
        """Registra el fallecimiento de una persona"""
        hoy = date.today()
        fecha_fallecimiento = hoy.strftime("%Y-%m-%d")
        
        # Actualizar la persona directamente en la matriz
        persona["fecha_defuncion"] = fecha_fallecimiento
        
        # Corrección: Solo cambiar a viudo si estaba casado
        estado_actual = persona.get("estado_civil", "")
        if estado_actual.lower() in ["casado", "casada"]:
            persona["estado_civil"] = "Viudo"
        # Si no estaba casado, mantener el estado actual o poner Soltero
        elif not estado_actual:
            persona["estado_civil"] = "Soltero"
        # Si tenía otro estado (soltero, viudo, etc.), mantenerlo
        
        logger.info(f"Fallecimiento: {persona.get('nombre')} {persona.get('apellidos')}")
        
        return {
            "nombre": persona.get("nombre", ""),
            "apellidos": persona.get("apellidos", ""),
            "fecha_fallecimiento": fecha_fallecimiento,
            "ubicacion": f"Fila {fila}, Columna {col}, Índice {idx}"
        }
    
    def _actualizar_pareja_viuda(self, fallecido: Dict, matriz: List, fila_fallecido: int, col_fallecido: int):
        """Actualiza el estado civil de la pareja del fallecido"""
        try:
            # Verificar que la fila sea de parejas (0 o 2)
            if fila_fallecido in [0, 2]:
                # Buscar la celda de la pareja
                if col_fallecido < len(matriz[fila_fallecido]):
                    celda = matriz[fila_fallecido][col_fallecido]
                    # Encontrar a la otra persona en la pareja
                    for persona in celda:
                        # Si no es el fallecido y está vivo
                        if (persona.get("nombre") != fallecido.get("nombre") and 
                            not persona.get("fecha_defuncion")):
                            # Solo cambiar a viudo si estaba casado
                            estado_actual = persona.get("estado_civil", "")
                            if estado_actual.lower() in ["casado", "casada"]:
                                persona["estado_civil"] = "Viudo"
                                logger.info(f"Pareja viuda actualizada: {persona.get('nombre')}")
                            break
        except Exception as e:
            logger.error(f"Error actualizando pareja viuda: {e}")
    
    def _parse_fecha(self, fecha_str: str) -> Optional[date]:
        """Parsea una fecha desde string"""
        if not fecha_str:
            return None
        try:
            return datetime.strptime(fecha_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

# Instancia global para uso en la aplicación
gestor_fallecimientos = GestorFallecimientos()