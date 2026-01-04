"""Herramientas MCP para consulta de registros de entrada/salida"""

from typing import Optional
from datetime import datetime
from sqlalchemy import text
from ..utils.fechas import get_current_date


async def consultar_registros_fecha(
    db,
    fecha: str,
    empleado_id: Optional[str] = None,
    restaurante: Optional[str] = None,
    tipo: Optional[str] = None
) -> dict:
    """
    Consulta registros de una fecha específica.

    Args:
        db: Instancia de Database
        fecha: Fecha en formato YYYY-MM-DD
        empleado_id: UUID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)
        tipo: ENTRADA o SALIDA (opcional)

    Returns:
        Lista de registros con datos del empleado
    """
    query = """
        SELECT
            r.id,
            r.empleado_id,
            e.codigo_empleado,
            e.nombre || ' ' || e.apellido AS empleado_nombre,
            e.cargo,
            e.departamento,
            r.tipo_registro,
            r.punto_trabajo,
            r.fecha_registro,
            r.hora_registro,
            r.timestamp_registro,
            r.confianza_reconocimiento,
            r.observaciones
        FROM registros r
        JOIN empleados e ON r.empleado_id = e.id
        WHERE r.fecha_registro = :fecha
          AND (CAST(:empleado_id AS uuid) IS NULL OR r.empleado_id = CAST(:empleado_id AS uuid))
          AND (CAST(:restaurante AS text) IS NULL OR r.punto_trabajo ILIKE ('%' || CAST(:restaurante AS text) || '%'))
          AND (CAST(:tipo AS text) IS NULL OR r.tipo_registro = :tipo)
        ORDER BY r.hora_registro
    """
    
    
    params = {
        'fecha': datetime.strptime(fecha, '%Y-%m-%d').date(),
        'empleado_id': empleado_id,
        'restaurante': restaurante,
        'tipo': tipo
    }
    
    results = await db.execute(query, params)
    
    registros = []
    for row in results:
        registros.append({
            'id': str(row['id']),
            'empleado_id': str(row['empleado_id']),
            'codigo_empleado': row['codigo_empleado'],
            'empleado_nombre': row['empleado_nombre'],
            'cargo': row['cargo'],
            'departamento': row['departamento'],
            'tipo_registro': row['tipo_registro'],
            'punto_trabajo': row['punto_trabajo'],
            'fecha_registro': str(row['fecha_registro']),
            'hora_registro': str(row['hora_registro']),
            'confianza': float(row['confianza_reconocimiento']) if row['confianza_reconocimiento'] else None,
            'observaciones': row['observaciones']
        })
    
    return {
        'fecha': fecha,
        'filtros': {
            'empleado_id': empleado_id,
            'restaurante': restaurante,
            'tipo': tipo
        },
        'total_registros': len(registros),
        'registros': registros
    }


async def consultar_registros_rango(
    db,
    fecha_inicio: str,
    fecha_fin: str,
    empleado_id: Optional[str] = None,
    restaurante: Optional[str] = None
) -> dict:
    """
    Consulta registros en un rango de fechas.

    Args:
        db: Instancia de Database
        fecha_inicio: Fecha inicio YYYY-MM-DD
        fecha_fin: Fecha fin YYYY-MM-DD
        empleado_id: UUID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)

    Returns:
        Lista de registros ordenados por fecha y hora
    """
    query = """
        SELECT
            r.id,
            r.empleado_id,
            e.codigo_empleado,
            e.nombre || ' ' || e.apellido AS empleado_nombre,
            r.tipo_registro,
            r.punto_trabajo,
            r.fecha_registro,
            r.hora_registro,
            r.observaciones
        FROM registros r
        JOIN empleados e ON r.empleado_id = e.id
        WHERE r.fecha_registro BETWEEN :fecha_inicio AND :fecha_fin
          AND (CAST(:empleado_id AS uuid) IS NULL OR r.empleado_id = CAST(:empleado_id AS uuid))
          AND (CAST(:restaurante AS text) IS NULL OR r.punto_trabajo ILIKE ('%' || CAST(:restaurante AS text) || '%'))
        ORDER BY r.fecha_registro, r.hora_registro
    """
    
    params = {
        'fecha_inicio': datetime.strptime(fecha_inicio, '%Y-%m-%d').date(),
        'fecha_fin': datetime.strptime(fecha_fin, '%Y-%m-%d').date(),
        'empleado_id': empleado_id,
        'restaurante': restaurante
    }
    
    results = await db.execute(query, params)
    
    registros = []
    for row in results:
        registros.append({
            'id': str(row['id']),
            'empleado_id': str(row['empleado_id']),
            'codigo_empleado': row['codigo_empleado'],
            'empleado_nombre': row['empleado_nombre'],
            'tipo_registro': row['tipo_registro'],
            'punto_trabajo': row['punto_trabajo'],
            'fecha_registro': str(row['fecha_registro']),
            'hora_registro': str(row['hora_registro']),
            'observaciones': row['observaciones']
        })
    
    return {
        'periodo': {
            'inicio': fecha_inicio,
            'fin': fecha_fin
        },
        'filtros': {
            'empleado_id': empleado_id,
            'restaurante': restaurante
        },
        'total_registros': len(registros),
        'registros': registros
    }


async def obtener_ultimo_registro(db, empleado_id: str) -> dict:
    """
    Obtiene el último registro de un empleado.

    Args:
        db: Instancia de Database
        empleado_id: UUID del empleado

    Returns:
        Último registro y siguiente acción esperada
    """
    query = """
        SELECT
            r.tipo_registro,
            r.fecha_registro,
            r.hora_registro,
            r.punto_trabajo,
            e.nombre || ' ' || e.apellido AS empleado_nombre
        FROM registros r
        JOIN empleados e ON r.empleado_id = e.id
        WHERE r.empleado_id = CAST(:empleado_id AS uuid)
        ORDER BY r.fecha_registro DESC, r.hora_registro DESC
        LIMIT 1
    """
    
    result = await db.execute_one(query, {'empleado_id': empleado_id})
    
    if result:
        siguiente_accion = 'SALIDA' if result['tipo_registro'] == 'ENTRADA' else 'ENTRADA'
        return {
            'empleado_id': empleado_id,
            'empleado_nombre': result['empleado_nombre'],
            'ultimo_registro': {
                'tipo': result['tipo_registro'],
                'fecha': str(result['fecha_registro']),
                'hora': str(result['hora_registro']),
                'punto_trabajo': result['punto_trabajo']
            },
            'siguiente_accion': siguiente_accion
        }
    else:
        return {
            'empleado_id': empleado_id,
            'empleado_nombre': None,
            'ultimo_registro': None,
            'siguiente_accion': 'ENTRADA',
            'mensaje': 'No hay registros para este empleado'
        }


async def empleados_sin_salida(db, fecha: Optional[str] = None) -> dict:
    """
    Lista empleados con entrada pero sin salida registrada.

    Args:
        db: Instancia de Database
        fecha: Fecha YYYY-MM-DD (opcional, default: hoy)

    Returns:
        Lista de empleados pendientes
    """
    if fecha is None:
        fecha = str(get_current_date())
    
    query = """
        WITH entradas AS (
            SELECT
                empleado_id,
                MIN(hora_registro) AS primera_entrada,
                punto_trabajo
            FROM registros
            WHERE fecha_registro = :fecha
              AND tipo_registro = 'ENTRADA'
            GROUP BY empleado_id, punto_trabajo
        ),
        salidas AS (
            SELECT DISTINCT empleado_id
            FROM registros
            WHERE fecha_registro = :fecha
              AND tipo_registro = 'SALIDA'
        )
        SELECT
            e.id AS empleado_id,
            e.codigo_empleado,
            e.nombre || ' ' || e.apellido AS empleado_nombre,
            en.primera_entrada AS hora_entrada,
            en.punto_trabajo,
            EXTRACT(EPOCH FROM (NOW() - (CAST(:fecha AS date) + en.primera_entrada))) / 3600 AS horas_transcurridas
        FROM entradas en
        JOIN empleados e ON en.empleado_id = e.id
        LEFT JOIN salidas s ON en.empleado_id = s.empleado_id
        WHERE s.empleado_id IS NULL
        ORDER BY en.primera_entrada
    """
    
    results = await db.execute(query, {'fecha': fecha})
    
    empleados = []
    for row in results:
        empleados.append({
            'empleado_id': str(row['empleado_id']),
            'codigo_empleado': row['codigo_empleado'],
            'empleado_nombre': row['empleado_nombre'],
            'hora_entrada': str(row['hora_entrada']),
            'punto_trabajo': row['punto_trabajo'],
            'horas_transcurridas': round(float(row['horas_transcurridas']), 2) if row['horas_transcurridas'] else 0
        })
    
    return {
        'fecha': fecha,
        'total_sin_salida': len(empleados),
        'empleados': empleados
    }

async def maintenance_buscar_typos(db) -> dict:
    """
    Busca el typo 'Leños Y Parrila' en varias tablas/campos
    """
    results = {}
    
    # Check registros.punto_trabajo (should be 0 now after previous fix)
    q1 = "SELECT COUNT(*) as count FROM registros WHERE punto_trabajo ILIKE '%Leños%Parrila%'"
    r1 = await db.execute_one(q1)
    results["registros.punto_trabajo"] = r1["count"] if r1 else 0
    
    # Check empleados.punto_trabajo
    q2 = "SELECT COUNT(*) as count FROM empleados WHERE punto_trabajo ILIKE '%Leños%Parrila%'"
    r2 = await db.execute_one(q2)
    results["empleados.punto_trabajo"] = r2["count"] if r2 else 0
    
    # Check empleados.departamento
    q3 = "SELECT COUNT(*) as count FROM empleados WHERE departamento ILIKE '%Leños%Parrila%'"
    r3 = await db.execute_one(q3)
    results["empleados.departamento"] = r3["count"] if r3 else 0
    
    return {
        "resultados": results,
        "mensaje": "Búsqueda de typos completada."
    }

async def maintenance_descubrir_esquema(db) -> dict:
    """
    Busca todas las tablas que tengan columnas de texto y escanea por el typo
    """
    # 1. Listar todas las tablas y columnas
    q_tables = """
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND data_type IN ('text', 'character varying')
    """
    tables = await db.execute(q_tables)
    
    findings = []
    
    for row in tables:
        table = row['table_name']
        column = row['column_name']
        
        # Ignorar tablas de sistema si hay alguna
        if table.startswith('pg_'): continue
        
        q_check = f"SELECT COUNT(*) as count FROM {table} WHERE {column} ILIKE '%Leños%Parrila%'"
        try:
            r = await db.execute_one(q_check)
            count = r['count'] if r else 0
            if count > 0:
                findings.append({
                    "tabla": table,
                    "columna": column,
                    "cantidad": count
                })
        except:
            continue
            
    return {
        "hallazgos": findings,
        "total_tablas_escaneadas": len(set(t['table_name'] for t in tables))
    }

async def mantenimiento_limpiar_puntos(db) -> dict:
    """
    Herramienta TEMPORAL para corregir errores tipográficos en los nombres de restaurantes.
    """
    # Fix registros
    u1 = "UPDATE registros SET punto_trabajo = 'Leños y Parrilla' WHERE punto_trabajo ILIKE '%Leños%Parrila%'"
    # Fix empleados
    u2 = "UPDATE empleados SET punto_trabajo = 'Leños y Parrilla' WHERE punto_trabajo ILIKE '%Leños%Parrila%'"
    u3 = "UPDATE empleados SET departamento = 'Leños y Parrilla' WHERE departamento ILIKE '%Leños%Parrila%'"
    
    try:
        async with db.session_factory() as session:
            await session.execute(text(u1))
            await session.execute(text(u2))
            await session.execute(text(u3))
            await session.commit()
    except Exception as e:
        if "does not return rows" not in str(e):
            raise e
            
    return {"mensaje": "Limpieza profunda completada."}
