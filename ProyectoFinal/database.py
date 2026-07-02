import sqlite3
from datetime import date
import calendar
from config import DB_FILE, PRESUPUESTOS_POR_EQUIPO

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_consumidor TEXT NOT NULL
            )
        ''')
        
        # Tabla de peticiones (Historial)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS peticiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                tipo_consumidor TEXT,
                coste_peticion REAL,
                tokens_peticion REAL,
                coste_maximo REAL,
                porcentaje_ahorro REAL,
                dia DATE,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        ''')
        
        # Insertar usuarios de prueba si la tabla está vacía
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        if cursor.fetchone()[0] == 0:
            usuarios_demo = [
                ("marketing",),
                ("produccion",),
                ("frontend",),
                ("backend",),
                ("backend",) # Agregado para probar presupuestos altos
            ]
            cursor.executemany("INSERT INTO usuarios (tipo_consumidor) VALUES (?)", usuarios_demo)
            
        conn.commit()

def obtener_tipo_consumidor(usuario_id: int) -> str | None:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tipo_consumidor FROM usuarios WHERE id = ?", (usuario_id,))
        resultado_usuario = cursor.fetchone()
        return resultado_usuario[0] if resultado_usuario else None

def obtener_gasto_y_dias_activos(usuario_id: int, año_mes: str) -> tuple[float, int]:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUM(coste_peticion), COUNT(DISTINCT dia) 
            FROM peticiones 
            WHERE usuario_id = ? AND substr(dia, 1, 7) = ?
        ''', (usuario_id, año_mes))
        resultado = cursor.fetchone()
        gasto_actual = resultado[0] or 0.0
        dias_activos = resultado[1] or 1
        return gasto_actual, dias_activos

def obtener_usuarios_lista() -> list[dict]:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, tipo_consumidor FROM usuarios")
        filas = cursor.fetchall()
        return [{"id": fila[0], "tipo_consumidor": fila[1]} for fila in filas]

def obtener_coste_diario_usuario(usuario_id: int, hoy_str: str) -> tuple[float, float, int]:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUM(coste_peticion), SUM(tokens_peticion), COUNT(id)
            FROM peticiones
            WHERE usuario_id = ? AND dia = ?
        ''', (usuario_id, hoy_str))
        resultado = cursor.fetchone()
        coste_total = resultado[0] or 0.0
        tokens_totales = resultado[1] or 0.0
        num_peticiones = resultado[2] or 0
        return coste_total, tokens_totales, num_peticiones

def obtener_historial_usuario_lista(usuario_id: int) -> list[dict]:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, tokens_peticion, coste_peticion, dia
            FROM peticiones
            WHERE usuario_id = ?
            ORDER BY id ASC
        ''', (usuario_id,))
        filas = cursor.fetchall()
        return [
            {
                "identificador": f"Petición {i}",
                "id_bd": f[0],
                "tokens": f[1],
                "coste_usd": round(f[2], 10),
                "dia": f[3]
            }
            for i, f in enumerate(filas, start=1)
        ]

def registrar_peticion(usuario_id: int, tipo_consumidor: str, coste_total_usd: float, tokens_totales: float, coste_maximo: float, porcentaje_ahorro: float, hoy_str: str) -> str:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO peticiones (usuario_id, tipo_consumidor, coste_peticion, tokens_peticion, coste_maximo, porcentaje_ahorro, dia)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (usuario_id, tipo_consumidor, coste_total_usd, tokens_totales, coste_maximo, porcentaje_ahorro, hoy_str))
            conn.commit()
        return "registrado_ok"
    except Exception as e:
        return f"error_db: {e}"

def obtenerGatosDiarios() -> list[dict]:
    # 1. Obtenemos la fecha actual
    hoy_str = date.today().isoformat()
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # 2. Hacemos un LEFT JOIN filtrando las peticiones sólo al día actual
        # COALESCE convierte los nulls en 0.0 para usuarios sin gasto hoy
        cursor.execute('''
            SELECT u.id, u.tipo_consumidor, COALESCE(SUM(p.coste_peticion), 0) AS gasto_diario
            FROM usuarios u
            LEFT JOIN peticiones p ON u.id = p.usuario_id AND p.dia = ?
            GROUP BY u.id, u.tipo_consumidor
            ORDER BY u.id ASC
        ''', (hoy_str,))
        
        filas = cursor.fetchall()
        
        resultado = []
        for fila in filas:
            usuario_id = fila[0]
            tipo_consumidor = fila[1]
            gasto_diario = round(fila[2], 10)
            
            # 3. Obtenemos el límite diario directamente del presupuesto por equipo
            limite_diario = PRESUPUESTOS_POR_EQUIPO.get(tipo_consumidor, 0.0001)
            
            # 4. Agregamos el resultado calculando el porcentaje del día
            resultado.append({
                "id": usuario_id,
                "tipo_consumidor": tipo_consumidor,
                "gasto_diario_actual": gasto_diario,
                "limite_de_gasto": limite_diario,
                "porcentaje_gasto": round((gasto_diario / limite_diario) * 100, 2) if limite_diario > 0 else 0.0
            })
            
        return resultado
    

def obtenerAhorrosMensuales(usuario_id: int) -> list[dict]:
    # Obtenemos el mes actual
    hoy = date.today()
    mes_actual = hoy.strftime("%Y-%m")
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Solución: En vez de coger un 'porcentaje_ahorro' de una fila suelta, 
        # sumamos todos los costes reales y máximos del mes.
        cursor.execute('''
            SELECT u.id, 
                   COALESCE(SUM(p.coste_peticion), 0) AS coste_total,
                   COALESCE(SUM(p.coste_maximo), 0) AS coste_maximo_total
            FROM usuarios u 
            LEFT JOIN peticiones p ON u.id = p.usuario_id AND substr(p.dia, 1, 7) = ?
            WHERE u.id = ?
            GROUP BY u.id
        ''', (mes_actual, usuario_id))
        
        fila = cursor.fetchone() 

        # Si el usuario no existe, devolvemos una lista vacía
        if not fila:
            return []

        # Extraemos los datos agregados
        id_usuario, coste_total, coste_maximo_total = fila
        
        # Calculamos el ahorro total en dólares del mes
        ahorro_mensual = coste_maximo_total - coste_total
        
        # Calculamos el porcentaje mensual basados en los totales reales
        if coste_maximo_total > 0:
            porcentaje_ahorro = 100 - (coste_total * 100 / coste_maximo_total)
        else:
            porcentaje_ahorro = 0.0
        
        return [{
            "id": id_usuario,
            "ahorro_mensual": round(ahorro_mensual, 10),
            "porcentaje_ahorro": round(porcentaje_ahorro, 2)
        }]