# services/db.py
# Estructura: { "NombreFamilia": matriz }
# Donde matriz = lista de filas (niveles generacionales)
#   cada fila = lista de columnas (subfamilias)
#   cada celda = lista de personas (dicts)

from typing import Dict, List, Tuple

FamiliaMatriz = List[List[List[dict]]]
familias: Dict[str, FamiliaMatriz] = {}

# ------------------ API base ------------------

def crear_familia(nombre: str) -> bool:
    """Crea una familia con matriz vacía. Devuelve False si ya existe o nombre vacío."""
    nombre = (nombre or "").strip()
    if not nombre or nombre in familias:
        return False
    familias[nombre] = []  # matriz vacía
    return True

def listar_familias() -> List[str]:
    """Lista los nombres de familias existentes."""
    return list(familias.keys())

def existe_familia(nombre: str) -> bool:
    return nombre in familias

def obtener_matriz(nombre: str) -> FamiliaMatriz | None:
    """Devuelve la matriz de una familia o None si no existe."""
    return familias.get(nombre)

def limpiar_familia(nombre: str) -> bool:
    """Resetea la matriz de una familia concreta."""
    if nombre in familias:
        familias[nombre] = []
        return True
    return False

def limpiar_todo() -> None:
    """Elimina todas las familias y datos (¡cuidado!)."""
    familias.clear()

def _tamano_dinamico(matriz: FamiliaMatriz, fila: int, columna: int) -> None:
    """Asegura que la matriz tenga al menos [fila][columna]."""
    while len(matriz) <= fila:
        matriz.append([])
    while len(matriz[fila]) <= columna:
        matriz[fila].append([])

def agregar_persona(persona: dict, nombre_familia: str, fila: int, columna: int) -> None:
    """
    Inserta una persona en la familia y posición dados.
    Lanza ValueError si la familia no existe.
    """
    if not existe_familia(nombre_familia):
        raise ValueError("Familia no seleccionada o no existe")

    m = familias[nombre_familia]
    _tamano_dinamico(m, fila, columna)
    m[fila][columna].append(persona)

# ------------------ Helpers de seed ------------------

# Provincia por columna (puedes ajustar si querés otro mapeo por rama)
RESIDENCIA_POR_COL = {
    0: "San José",
    1: "Alajuela",
    2: "Cartago",
    3: "Heredia",
    4: "Guanacaste",
}

# Prefijo de cédula (primer dígito) según provincia
PROV_PREFIJO = {
    "San José": "1",
    "Alajuela": "2",
    "Cartago": "3",
    "Heredia": "4",
    "Guanacaste": "5",
    "Puntarenas": "6",
    "Limón": "7",
}

# Contadores por provincia para generar números únicos
_contador_por_prov: Dict[str, int] = {}
# Para reutilizar la misma cédula si la persona aparece en varios niveles
_cedulas_persona: Dict[Tuple[str, str, str], str] = {}

def _cedula(provincia: str, anio: int, persona_key: Tuple[str, str, str]) -> str:
    """Genera (o reutiliza) una cédula numérica: <prefijo_prov><YYYY><####>."""
    # Reutiliza si ya existe
    if persona_key in _cedulas_persona:
        return _cedulas_persona[persona_key]

    pref = PROV_PREFIJO.get(provincia, "1")
    _contador_por_prov[provincia] = _contador_por_prov.get(provincia, 0) + 1
    sec = _contador_por_prov[provincia]
    ced = f"{pref}{anio:04d}{sec:04d}"  # ej: 1 1970 0001 -> "119700001"
    _cedulas_persona[persona_key] = ced
    return ced

def _p_col(
    col: int,
    nombre: str,
    apellidos: str,
    genero: str,
    tag: str,                 # solo decorativo; no se usa para la cédula
    fecha_nac: str,           # "YYYY-MM-DD"
    residencia: str | None = None,
    estado_civil: str = "Soltero",
    fecha_def: str = "",
) -> dict:
    """Crea el dict persona con residencia por columna y cédula numérica coherente."""
    prov = residencia or RESIDENCIA_POR_COL.get(col, "San José")
    anio = int(fecha_nac[:4])
    key = (nombre, apellidos, fecha_nac)
    ced = _cedula(prov, anio, key)
    return {
        "nombre": nombre,
        "apellidos": apellidos,
        "cedula": ced,
        "fecha_nacimiento": fecha_nac,
        "fecha_defuncion": fecha_def,
        "genero": genero,
        "residencia": prov,
        "estado_civil": estado_civil,
    }

# ------------------ Seed: Familia Espinoza Gonzales ------------------

def _seed_familia_espinoza():
    fam = "Espinoza Gonzales"
    if not crear_familia(fam):
        return  # ya existe

    # Fila , Columna
    # Nivel 0 (parejas fundadoras)
    agregar_persona(_p_col(0, "Edgardo", "Espinoza Juarez", "Masculino", "EJ-1970-0001", "1970-05-12", estado_civil="Casado"), fam, 0, 0)
    agregar_persona(_p_col(0, "María",   "Sanchez Gonzales", "Femenino", "MS-1972-0002", "1972-09-03", estado_civil="Casado"), fam, 0, 0)

    agregar_persona(_p_col(1, "Carlos",  "Rojas Vargas",    "Masculino", "CR-1969-0003", "1969-03-22", estado_civil="Casado"), fam, 0, 1)
    agregar_persona(_p_col(1, "Daniela", "Lopez Mendez",    "Femenino",  "DL-1971-0004", "1971-11-10", estado_civil="Casado"), fam, 0, 1)

    # Nivel 1 (hijos: 3 por pareja)
    # Hijos de Edgardo + María (col 0)
    agregar_persona(_p_col(0, "Luis",     "Espinoza Sanchez", "Masculino", "LE-1993-1001", "1993-02-15"), fam, 1, 0)
    agregar_persona(_p_col(0, "Fernanda", "Espinoza Sanchez", "Femenino",  "FE-1995-1002", "1995-07-21"), fam, 1, 0)
    agregar_persona(_p_col(0, "Gabriel",  "Espinoza Sanchez", "Masculino", "GE-1992-1003", "1992-12-03"), fam, 1, 0)

    # Hijos de Carlos + Daniela (col 1)
    agregar_persona(_p_col(1, "Andrea", "Rojas Lopez", "Femenino", "AR-1994-2001", "1994-04-09"), fam, 1, 1)
    agregar_persona(_p_col(1, "Mateo",  "Rojas Lopez", "Masculino","MR-1991-2002", "1991-08-18"), fam, 1, 1)
    agregar_persona(_p_col(1, "Sofía",  "Rojas Lopez", "Femenino", "SR-1996-2003", "1996-10-27"), fam, 1, 1)

    # Nivel 2 (parejas de los hijos)
    # Cruce: Luis (col 0) + Andrea (col 1) → los ubicamos en col 0
    agregar_persona(_p_col(0, "Luis",   "Espinoza Sanchez", "Masculino", "LE-1993-1001", "1993-02-15", estado_civil="Casado"), fam, 2, 0)
    agregar_persona(_p_col(0, "Andrea", "Rojas Lopez",      "Femenino",  "AR-1994-2001", "1994-04-09", estado_civil="Casado"), fam, 2, 0)

    # Fernanda + Ricardo (random) → col 1
    agregar_persona(_p_col(1, "Fernanda", "Espinoza Sanchez", "Femenino",  "FE-1995-1002", "1995-07-21", estado_civil="Casado"), fam, 2, 1)
    agregar_persona(_p_col(1, "Ricardo",  "Morales Quesada",  "Masculino", "RM-1990-3001", "1990-06-29", estado_civil="Casado"), fam, 2, 1)

    # Gabriel + Karina → col 2
    agregar_persona(_p_col(2, "Gabriel", "Espinoza Sanchez", "Masculino", "GE-1992-1003", "1992-12-03", estado_civil="Casado"), fam, 2, 2)
    agregar_persona(_p_col(2, "Karina",  "Ramirez Solano",   "Femenino",  "KR-1993-3002", "1993-01-14", estado_civil="Casado"), fam, 2, 2)

    # Mateo + Valeria → col 3
    agregar_persona(_p_col(3, "Mateo",   "Rojas Lopez",  "Masculino", "MR-1991-2002", "1991-08-18", estado_civil="Casado"), fam, 2, 3)
    agregar_persona(_p_col(3, "Valeria", "Campos Araya", "Femenino",  "VC-1992-3003", "1992-05-05", estado_civil="Casado"), fam, 2, 3)

    # Sofía + Diego → col 4
    agregar_persona(_p_col(4, "Sofía", "Rojas Lopez",       "Femenino",  "SR-1996-2003", "1996-10-27", estado_civil="Casado"), fam, 2, 4)
    agregar_persona(_p_col(4, "Diego", "Hernandez Cordero", "Masculino", "DH-1990-3004", "1990-09-01", estado_civil="Casado"), fam, 2, 4)

    # Nivel 3 (2 hijos por pareja del nivel 2)
    # Hijos de Luis + Andrea → col 0
    agregar_persona(_p_col(0, "Nicolás", "Espinoza Rojas", "Masculino", "NR-2018-4001", "2018-03-12"), fam, 3, 0)
    agregar_persona(_p_col(0, "Camila",  "Espinoza Rojas", "Femenino",  "CR-2020-4002", "2020-07-25"), fam, 3, 0)

    # Hijos de Fernanda + Ricardo → col 1
    agregar_persona(_p_col(1, "Samuel", "Morales Espinoza", "Masculino", "SE-2017-4101", "2017-11-05"), fam, 3, 1)
    agregar_persona(_p_col(1, "Lucía",  "Morales Espinoza", "Femenino",  "LE-2019-4102", "2019-02-19"), fam, 3, 1)

    # Hijos de Gabriel + Karina → col 2
    agregar_persona(_p_col(2, "Daniel",    "Espinoza Ramirez", "Masculino", "DR-2016-4201", "2016-06-17"), fam, 3, 2)
    agregar_persona(_p_col(2, "Valentina", "Espinoza Ramirez", "Femenino",  "VR-2021-4202", "2021-01-09"), fam, 3, 2)

    # Hijos de Mateo + Valeria → col 3
    agregar_persona(_p_col(3, "Tomás", "Rojas Campos", "Masculino", "TC-2015-4301", "2015-04-02"), fam, 3, 3)
    agregar_persona(_p_col(3, "Emma",  "Rojas Campos", "Femenino",  "EC-2018-4302", "2018-09-23"), fam, 3, 3)

    # Hijos de Sofía + Diego → col 4
    agregar_persona(_p_col(4, "Martín", "Hernandez Rojas", "Masculino", "MR-2017-4401", "2017-08-30"), fam, 3, 4)
    agregar_persona(_p_col(4, "Sara",   "Hernandez Rojas", "Femenino",  "SR-2020-4402", "2020-12-12"), fam, 3, 4)


# ------------------ Seed: Familia Alvarez Mendez ------------------

def _seed_familia_alvarez_mendez():
    fam = "Alvarez Mendez"
    if not crear_familia(fam):
        return  # ya existe

    # Fila , Columna

    # Nivel 0 (parejas fundadoras)
    agregar_persona(_p_col(0, "Jorge",   "Alvarez Salas",   "Masculino", "JA-1971-0001", "1971-02-14", estado_civil="Casado"), fam, 0, 0)
    agregar_persona(_p_col(0, "Laura",   "Mendez Pineda",   "Femenino",  "LP-1973-0002", "1973-07-09", estado_civil="Casado"), fam, 0, 0)

    agregar_persona(_p_col(1, "Hector",  "Vargas Cordero",  "Masculino", "HV-1968-0003", "1968-11-23", estado_civil="Casado"), fam, 0, 1)
    agregar_persona(_p_col(1, "Patricia","Quesada Mora",    "Femenino",  "PQ-1970-0004", "1970-04-30", estado_civil="Casado"), fam, 0, 1)

    # Nivel 1 (hijos: 3 por pareja)
    # Hijos de Jorge + Laura (col 0): apellidos Alvarez Mendez
    agregar_persona(_p_col(0, "Diego",     "Alvarez Mendez", "Masculino", "DA-1994-1001", "1994-03-01"), fam, 1, 0)
    agregar_persona(_p_col(0, "Isabel",    "Alvarez Mendez", "Femenino",  "IA-1996-1002", "1996-08-12"), fam, 1, 0)
    agregar_persona(_p_col(0, "Sebastian", "Alvarez Mendez", "Masculino", "SA-1992-1003", "1992-12-20"), fam, 1, 0)

    # Hijos de Hector + Patricia (col 1): apellidos Vargas Quesada
    agregar_persona(_p_col(1, "Paula",   "Vargas Quesada", "Femenino",  "PV-1995-2001", "1995-06-18"), fam, 1, 1)
    agregar_persona(_p_col(1, "Andres",  "Vargas Quesada", "Masculino", "AV-1991-2002", "1991-10-05"), fam, 1, 1)
    agregar_persona(_p_col(1, "Valeria", "Vargas Quesada", "Femenino",  "VV-1997-2003", "1997-01-27"), fam, 1, 1)

    # Nivel 2 (parejas de los hijos)
    # Cruce: Diego (col 0) + Paula (col 1) → ubicados en col 0
    agregar_persona(_p_col(0, "Diego",  "Alvarez Mendez",  "Masculino", "DA-1994-1001", "1994-03-01", estado_civil="Casado"), fam, 2, 0)
    agregar_persona(_p_col(0, "Paula",  "Vargas Quesada",  "Femenino",  "PV-1995-2001", "1995-06-18", estado_civil="Casado"), fam, 2, 0)

    # Isabel + Mauricio Solano Brenes → col 1
    agregar_persona(_p_col(1, "Isabel",   "Alvarez Mendez", "Femenino",  "IA-1996-1002", "1996-08-12", estado_civil="Casado"), fam, 2, 1)
    agregar_persona(_p_col(1, "Mauricio", "Solano Brenes",  "Masculino", "MS-1990-3001", "1990-09-14", estado_civil="Casado"), fam, 2, 1)

    # Sebastian + Karla Jimenez Araya → col 2
    agregar_persona(_p_col(2, "Sebastian", "Alvarez Mendez", "Masculino", "SA-1992-1003", "1992-12-20", estado_civil="Casado"), fam, 2, 2)
    agregar_persona(_p_col(2, "Karla",     "Jimenez Araya",  "Femenino",  "KJ-1993-3002", "1993-03-11", estado_civil="Casado"), fam, 2, 2)

    # Andres + Natalia Campos Rojas → col 3
    agregar_persona(_p_col(3, "Andres",  "Vargas Quesada", "Masculino", "AV-1991-2002", "1991-10-05", estado_civil="Casado"), fam, 2, 3)
    agregar_persona(_p_col(3, "Natalia", "Campos Rojas",   "Femenino",  "NC-1992-3003", "1992-08-07", estado_civil="Casado"), fam, 2, 3)

    # Valeria + Joaquin Hernandez Solis → col 4
    agregar_persona(_p_col(4, "Valeria", "Vargas Quesada",  "Femenino",  "VV-1997-2003", "1997-01-27", estado_civil="Casado"), fam, 2, 4)
    agregar_persona(_p_col(4, "Joaquin", "Hernandez Solis", "Masculino", "JH-1990-3004", "1990-05-22", estado_civil="Casado"), fam, 2, 4)

    # Nivel 3 (2 hijos por pareja del nivel 2)
    # Hijos de Diego + Paula → apellidos Alvarez Vargas → col 0
    agregar_persona(_p_col(0, "Mateo", "Alvarez Vargas", "Masculino", "MV-2019-4001", "2019-02-10"), fam, 3, 0)
    agregar_persona(_p_col(0, "Sofia", "Alvarez Vargas", "Femenino",  "SV-2021-4002", "2021-07-19"), fam, 3, 0)

    # Hijos de Isabel + Mauricio → apellidos Solano Alvarez → col 1
    agregar_persona(_p_col(1, "Lucas", "Solano Alvarez", "Masculino", "LA-2016-4101", "2016-11-03"), fam, 3, 1)
    agregar_persona(_p_col(1, "Ana",   "Solano Alvarez", "Femenino",  "AA-2019-4102", "2019-04-28"), fam, 3, 1)

    # Hijos de Sebastian + Karla → apellidos Alvarez Jimenez → col 2
    agregar_persona(_p_col(2, "Bruno", "Alvarez Jimenez", "Masculino", "BJ-2015-4201", "2015-06-30"), fam, 3, 2)
    agregar_persona(_p_col(2, "Luna",  "Alvarez Jimenez", "Femenino",  "LJ-2018-4202", "2018-09-12"), fam, 3, 2)

    # Hijos de Andres + Natalia → apellidos Vargas Campos → col 3
    agregar_persona(_p_col(3, "Iker", "Vargas Campos", "Masculino", "VC-2017-4301", "2017-01-21"), fam, 3, 3)
    agregar_persona(_p_col(3, "Mia",  "Vargas Campos", "Femenino",  "MC-2020-4302", "2020-03-15"), fam, 3, 3)

    # Hijos de Valeria + Joaquin → apellidos Hernandez Vargas → col 4
    agregar_persona(_p_col(4, "Gael", "Hernandez Vargas", "Masculino", "HV-2018-4401", "2018-05-09"), fam, 3, 4)
    agregar_persona(_p_col(4, "Zoe",  "Hernandez Vargas", "Femenino",  "ZV-2022-4402", "2022-02-17"), fam, 3, 4)

def _seed_defaults():
    _seed_familia_espinoza()
    _seed_familia_alvarez_mendez()

# Ejecutar seed al importar el módulo
_seed_defaults()
